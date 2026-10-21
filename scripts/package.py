#!/usr/bin/env python3
"""Assemble an inspectable host bundle with recursively resolved runtime libraries."""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from sources import ROOT, inputs, digest
from version import current_version, archive_stem

LINUX_SYSTEM = re.compile(r'^(?:ld-linux.*|lib(?:c|m|pthread|dl|rt|resolv|util|nss_[^.]+)\.so(?:\..*)?)$')
# Mesa and compositor plugins load against the host's graphics stack. Older
# bundled Wayland/GBM/DRM libraries can hide symbols required by those plugins.
LINUX_HOST_GRAPHICS = re.compile(
    r'^lib(?:wayland-(?:client|cursor|egl|server)|gbm|drm(?:_.*)?|'
    r'EGL(?:_.*)?|GL(?:X(?:_.*)?|dispatch)?|GLESv[12]|OpenGL|'
    r'vulkan(?:_.*)?)\.so(?:\..*)?$')

def rpaths(binary):
    lines = subprocess.check_output(['otool', '-l', str(binary)], text=True).splitlines()
    paths = []
    active = False
    for line in lines:
        if line.strip() == 'cmd LC_RPATH':
            active = True
        elif active and line.strip().startswith('path '):
            paths.append(line.strip().split(' (offset', 1)[0].removeprefix('path '))
            active = False
    return paths

def dependencies(binary, host, executable_dir=None):
    if host == 'linux':
        text = subprocess.check_output(['ldd', str(binary)], text=True)
        if 'not found' in text:
            raise RuntimeError('Unresolved ELF dependency: ' + str(binary))
        result = []
        for line in text.splitlines():
            match = re.search(r'=>\s+(/\S+)', line) or re.match(r'\s*(/\S+)\s+\(', line)
            if match:
                path = Path(match.group(1))
                if not (LINUX_SYSTEM.fullmatch(path.name) or
                        LINUX_HOST_GRAPHICS.fullmatch(path.name)):
                    result.append(path)
        return result
    if host == 'macos':
        lines = subprocess.check_output(['otool', '-L', str(binary)], text=True).splitlines()[1:]
        ids = subprocess.check_output(['otool', '-D', str(binary)], text=True).splitlines()[1:]
        own_id = ids[0].strip() if ids else None
        result = []
        def expand(name):
            if name.startswith('@loader_path/'):
                return binary.parent / name.removeprefix('@loader_path/')
            if name.startswith('@executable_path/'):
                return executable_dir / name.removeprefix('@executable_path/')
            return Path(name)
        for line in lines:
            name = line.strip().split(' (', 1)[0]
            if name == own_id or name.startswith(('/usr/lib/', '/System/Library/')):
                continue
            if name.startswith('@rpath/'):
                suffix = name.removeprefix('@rpath/')
                candidates = [expand(path) / suffix for path in rpaths(binary)]
                candidates.append(binary.parent / suffix)
                path = next((candidate for candidate in candidates if candidate.is_file()), None)
                if path is None:
                    raise RuntimeError('Unresolved Mach-O rpath dependency: ' + name)
            else:
                path = expand(name)
            if path.resolve() != binary.resolve():
                if not path.is_file():
                    raise RuntimeError('Missing Mach-O dependency: ' + name)
                result.append(path)
        return result
    text = subprocess.check_output(['objdump', '-p', str(binary)], text=True)
    roots = [binary.parent, Path(shutil.which('gcc')).parent]
    roots.extend(Path(p) for p in os.environ.get('PATH', '').split(os.pathsep) if p)
    system = Path(os.environ['SystemRoot']) / 'System32'
    result = []
    for name in re.findall(r'DLL Name:\s*(\S+)', text):
        if name.lower().startswith(('api-ms-win-', 'ext-ms-win-')) or (system / name).is_file():
            continue
        if name.lower().startswith(('msys-', 'cygwin')):
            raise RuntimeError('Portable bundle depends on an MSYS/Cygwin runtime: ' + name)
        found = next((directory / name for directory in roots if (directory / name).is_file()), None)
        if found is None:
            raise RuntimeError('Missing Windows runtime DLL: ' + name)
        result.append(found)
    return result

def bundle_libraries(binaries, destination, host):
    pending = list(binaries)
    executable_dir = next(iter(binaries)).parent
    copied = {}
    links = {}
    while pending:
        binary = pending.pop()
        required = dependencies(binary, host, executable_dir)
        links[binary] = required
        for source in required:
            name = source.name
            if name in copied:
                if digest(copied[name]) != digest(source):
                    raise RuntimeError('Runtime library name collision: ' + name)
                continue
            copied[name] = source
            shutil.copy2(source, destination / name)
            pending.append(source)
    if host == 'macos':
        for original, required in links.items():
            target = binaries[original] if original in binaries else destination / original.name
            target.chmod(target.stat().st_mode | 0o200)
            for dependency in required:
                # otool records symlink spelling; preserve that basename in the bundle.
                old_names = subprocess.check_output(['otool', '-L', str(original)], text=True).splitlines()[1:]
                for line in old_names:
                    old = line.strip().split(' (', 1)[0]
                    if old.endswith('/' + dependency.name):
                        replacement = '@loader_path/' + ('' if target.parent == destination else '../lib/') + dependency.name
                        subprocess.run(['install_name_tool', '-change', old, replacement, str(target)], check=True)
            for path in rpaths(original):
                subprocess.run(['install_name_tool', '-delete_rpath', path, str(target)], check=True)
            if target.parent == destination:
                subprocess.run(['install_name_tool', '-id', '@loader_path/' + target.name, str(target)], check=True)
            subprocess.run(['codesign', '--force', '--sign', '-', str(target)], check=True)
    return {name: digest(destination / name) for name in sorted(copied)}

def strip_debug(binary, host):
    # Mach-O's debug map contains absolute object paths added by the linker,
    # outside the compiler's -ffile-prefix-map handling. Strip before signing.
    option = '-S' if host == 'macos' else '--strip-debug'
    subprocess.run(['strip', option, str(binary)], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--platform', choices=('linux', 'macos', 'windows'), required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'out')
    pins = json.loads((ROOT / 'upstream.json').read_text())
    version = current_version()
    architecture = platform.machine().lower().replace('aarch64', 'arm64').replace('amd64', 'x86_64')
    name = archive_stem(args.platform + '-' + architecture)
    stage = output / name
    if stage.exists():
        raise FileExistsError('Preserve the previous bundle; use a new output directory')
    for directory in ('bin', 'lib', 'share/qemu', 'licenses', 'launch'):
        (stage / directory).mkdir(parents=True, exist_ok=True)
    executable_dir = stage / ('bin' if args.platform in ('windows', 'macos') else 'libexec')
    executable_dir.mkdir(exist_ok=True)
    binaries = {}
    extension = '.exe' if args.platform == 'windows' else ''
    for program in ('qemu-system-i386', 'qemu-system-sparc', 'qemu-system-hppa', 'qemu-img'):
        target = executable_dir / (program + extension)
        shutil.copy2(output / 'qemu' / (program + extension), target)
        strip_debug(target, args.platform)
        binaries[output / 'qemu' / (program + extension)] = target
        if args.platform == 'linux':
            wrapper = '#!/bin/sh\nset -eu\nroot=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)\nexport LD_LIBRARY_PATH="$root/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "$root/libexec/' + program + '"' + (' -L "$root/share/qemu"' if program != 'qemu-img' else '') + ' "$@"\n'
            (stage / 'bin' / program).write_text(wrapper)
            (stage / 'bin' / program).chmod(0o755)
    libraries = bundle_libraries(binaries, stage / ('bin' if args.platform == 'windows' else 'lib'), args.platform)
    firmware = ROOT / '.sources/qemu/pc-bios'
    for filename in ('vgabios.bin', 'vgabios-stdvga.bin', 'vgabios-vmware.bin', 'vgabios-cirrus.bin',
                     'kvmvapic.bin', 'linuxboot.bin', 'linuxboot_dma.bin', 'multiboot.bin', 'pvh.bin'):
        source = firmware / filename
        if source.is_file():
            shutil.copy2(source, stage / 'share/qemu' / filename)
    # TCX FCode is required for the SPARCstation framebuffer and console.
    shutil.copy2(firmware / 'QEMU,tcx.bin', stage / 'share/qemu/QEMU,tcx.bin')
    shutil.copytree(firmware / 'keymaps', stage / 'share/qemu/keymaps')
    for filename in ('bios.bin', 'bios-256k.bin'):
        shutil.copy2(output / 'firmware/bios.bin', stage / 'share/qemu' / filename)
    for filename in ('openbios-sparc32', 'hppa-firmware.img'):
        shutil.copy2(output / 'firmware' / filename, stage / 'share/qemu' / filename)
    # Catch accidental checkout paths even after stripping debug sections.
    # QEMU also embeds source locations in runtime diagnostics (__FILE__).
    for target in list(binaries.values()) + [stage / 'share/qemu' / name for name in
            ('bios.bin', 'openbios-sparc32', 'hppa-firmware.img')]:
        content = target.read_bytes()
        if any(prefix.encode() in content for prefix in (str(ROOT), ROOT.as_posix())):
            raise RuntimeError('Private checkout path in distributed binary: ' + target.name)
    for project in pins['projects']:
        for source in (ROOT / '.sources' / project).glob('COPYING*'):
            shutil.copy2(source, stage / 'licenses' / (project + '-' + source.name))
    shutil.copy2(ROOT / 'docs/bundle.md', stage / 'README.md')
    for source in (ROOT / 'launch').iterdir():
        if source.is_file():
            shutil.copy2(source, stage / 'launch' / source.name)
    results = json.loads((output / 'tests/results.json').read_text())
    manifest = {'schema': 1, 'distribution_version': version,
                'repository_commit': os.environ.get('GITHUB_SHA'),
                'platform': args.platform, 'architecture': architecture,
                'sources': {name: inputs(name)
                            for name, entry in pins['projects'].items()
                            if not entry.get('optional', False)},
                'firmware': json.loads((output / 'firmware/BUILD.json').read_text()),
                'debug_symbols_stripped': True,
                'qtests': results,
                'risc_qtests': json.loads((output / 'risc-tests/results.json').read_text()),
                'hppa_recovery': json.loads((output / 'hppa-recovery-tests/results.json').read_text()) if args.platform == 'linux' else None,
                'sparc_pte': json.loads((output / 'sparc-pte-tests/results.json').read_text()) if args.platform == 'linux' else None,
                'runtime_libraries': libraries,
                'tools': {'python': platform.python_version(),
                          'host_os_version': platform.mac_ver()[0] if args.platform == 'macos' else platform.release(),
                          'libc': list(platform.libc_ver()) if args.platform == 'linux' else None,
                          'compiler': subprocess.check_output(['cc' if args.platform != 'windows' else 'gcc', '--version'], text=True).splitlines()[0],
                          'ninja': subprocess.check_output(['ninja', '--version'], text=True).strip()},
                'configure_args': [('--python=<host-python>' if option.startswith('--python=') else option.replace(ROOT.as_posix(), '<source-root>').replace(str(ROOT), '<source-root>'))
                                   for option in json.loads((output / 'qemu/configure-args.json').read_text())],
                'guest_release_validated': False, 'dependency_license_source_audit_complete': False}
    (stage / 'BUILD.json').write_text(json.dumps(manifest, indent=2) + '\n')
    files = {str(f.relative_to(stage)): digest(f) for f in sorted(stage.rglob('*')) if f.is_file()}
    (stage / 'SHA256.json').write_text(json.dumps(files, indent=2) + '\n')
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    suffix = '.zip' if args.platform == 'windows' else '.tar.gz'
    archive = destination / (name + suffix)
    if archive.exists():
        raise FileExistsError('Do not overwrite existing distribution: ' + str(archive))
    if args.platform == 'windows':
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in sorted(stage.rglob('*')):
                if file.is_file():
                    z.write(file, str(file.relative_to(stage.parent)))
    else:
        with tarfile.open(archive, 'w:gz', format=tarfile.USTAR_FORMAT) as t:
            def metadata(member):
                member.uid = member.gid = 0
                member.uname = member.gname = 'root'
                member.mtime = 0
                return member
            t.add(stage, arcname=name, filter=metadata)
    archive.with_name(archive.name + '.sha256').write_text(digest(archive) + '  ' + archive.name + '\n')
    print('Built development bundle: ' + str(archive), flush=True)

if __name__ == '__main__':
    main()
