# Release preparation

## Automated publication

- Pushes to `master` build Linux x86-64, Windows x86-64, macOS arm64 and macOS
  x86-64, then update the `master-build` prerelease titled Latest master build.
- Pushes of `v*` tags build the same matrix and publish a versioned release.
  Tags with prerelease version suffixes remain prereleases.
- Pull requests to master build/test and upload artifacts without publishing.
- Manual runs on master can update its prerelease. The optional extended-tests
  input adds x86_64 SCSI coverage to Linux; downloads contain i386, SPARC and HPPA emulators
  plus qemu-img, without the optional x86_64 test emulator. Manual runs on other branches do not publish.

The publish job needs successful Linux, macOS (both matrix entries) and Windows
jobs. It independently checks all four archives, corresponding source, commit,
patch identities, payload hashes and shared PC, SPARC and HPPA firmware before touching a release.
Only that job has `contents: write`. The build jobs retain read-only permissions.

Asset names include the QEMU version and seven-character repository commit,
for example `openstep-qemu-11.1.1-a7a8f62-linux-x86_64.tar.gz`. Full commit, run
and attempt identities remain in build manifests. Uploads complete
before the rolling tag/notes change and old managed assets are removed. Build
failure, interrupted upload or a master commit superseded before promotion
retains the previous successful downloads. The GitHub API does not offer an
atomic transaction across asset uploads, tag movement and release editing;
new candidate assets can briefly coexist with the previous published set. A
rerun of the same commit replaces assets with the same filenames individually.
Published versioned assets are not overwritten; identical reruns are accepted.

Each release has four binary archives: Linux x86-64, Windows x86-64, macOS arm64
and macOS x86-64. Matching source, checksum sidecars and validation records remain
in the workflow artifacts; the release manifest stays in the publish job. Actions use the repository's
workflow token, not a separate personal token. Pushing master or a version tag
now authorizes the corresponding automatic publication behavior.

## Supported-release readiness

Rolling prereleases are development downloads, not a declaration that every
guest configuration or host baseline has been validated.

Before a supported release:

- Validate QEMU and the matching PC, SPARC and HPPA firmware together.
- Test portable bundles on Linux, Windows and both macOS host architectures.
- Exercise Intel NEXTSTEP 3.3 and OPENSTEP 4.2 separately, covering boot, input,
  graphics, network, audio, storage and services with their respective drivers. Separately check SPARC and HPPA installation, hard-disk boot, input,
  graphics, storage, debugging and clean shutdown; document unsupported devices.
- Complete runtime dependency license/notices and corresponding-source audit,
  including bundled firmware. The emulator/firmware source archive alone does not
  supply source for every dynamically bundled third-party host library.
- Select Linux glibc/OS and macOS/Windows minimum versions. Confirm that bundled
  library loading does not depend on the builder's package-manager paths.
- Decide Windows signing and macOS signing/notarization requirements.
- Map compiler source paths for release builds.
- Record source/configuration/compiler/tool versions, patch and binary hashes,
  test evidence, supported modes and known limits.

Release assets: four versioned platform bundles. Do not place binaries in Git history. Tags should
identify the recipe/patch collection; upstream versions remain separately pinned.
Individual patches retain upstream provenance and can be reviewed independently.
Guest drivers/services and EIDE downloads belong in `openstep-drivers`.

Linux and Windows distribution executables have debug symbols removed. Original
unstripped binaries remain in separate CI artifacts for seven days.
