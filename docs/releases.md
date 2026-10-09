# Release preparation

## Automated publication

- Pushes to `master` build Linux x86-64, Windows x86-64, macOS arm64 and macOS
  x86-64, then update the `master-build` prerelease titled Latest master build.
- Pushes of `v*` tags build the same matrix and publish a versioned release.
  Tags with prerelease version suffixes remain prereleases.
- Pull requests to master build/test and upload artifacts without publishing.
- Manual runs on master can update its prerelease. The optional extended-tests
  input adds x86_64 SCSI coverage to Linux; downloads still contain only i386
  and qemu-img. Manual runs on other branches do not publish.

The publish job needs successful Linux, macOS (both matrix entries) and Windows
jobs. It independently checks all four archives, corresponding source, commit,
patch identities, payload hashes and shared firmware before touching a release.
Only that job has `contents: write`. The build jobs retain read-only permissions.

Master asset names include commit, run and attempt identifiers. Uploads complete
before the rolling tag/notes change and old managed assets are removed. Build
failure, interrupted upload or a master commit superseded before promotion
retains the previous successful downloads. The GitHub API does not offer an
atomic transaction across asset uploads, tag movement and release editing;
new candidate assets can briefly coexist with the previous published set.
Published versioned assets are not overwritten; identical reruns are accepted.

Each release includes platform bundles, matching source, per-file checksums,
an aggregate checksum file and a release manifest. Actions use the repository's
workflow token, not a separate personal token. Pushing master or a version tag
now authorizes the corresponding automatic publication behavior.

## Supported-release readiness

Rolling prereleases are development downloads, not a declaration that every
OPENSTEP guest scenario or supported host baseline has been validated.

Before a supported release:

- Validate complete QEMU/SeaBIOS builds and affected guest paths together.
- Test portable bundles on Linux, Windows and both macOS host architectures.
- Exercise OPENSTEP boot, input, graphics, network, audio, storage and services.
- Complete runtime dependency license/notices and corresponding-source audit,
  including bundled firmware. The QEMU/SeaBIOS source archive alone does not
  supply source for every dynamically bundled third-party host library.
- Select Linux glibc/OS and macOS/Windows minimum versions. Confirm that bundled
  library loading does not depend on the builder's package-manager paths.
- Decide Windows signing and macOS signing/notarization requirements.
- Strip development debug data and map compiler source paths for release builds.
- Record source/configuration/compiler/tool versions, patch and binary hashes,
  test evidence, supported modes and known limits.

Release assets: versioned platform bundles, matching patched source/recipes,
checksums and build manifests. Do not place binaries in Git history. Tags should
identify the recipe/patch collection; upstream versions remain separately pinned.
Individual patches retain upstream provenance and can be reviewed independently.
Guest drivers/services and EIDE downloads belong in `openstep-drivers`.
