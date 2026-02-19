## v3.0.1

- Added short options for `projark` subcommands (#45, @kopardev):
  - common: `-f` (`--folder`), `-p` (`--projectnumber`), `-d` (`--datatype`)
  - deposit: `-t` (`--tarname`), `-s` (`--split-size-gb`), `-k` (`--no-cleanup`)
  - retrieve: `-n` (`--filenames`), `-u` (`--unsplit`/`--unspilt`)
- Updated `projectnumber` normalization (#44, @kopardev):
  - remove repeated leading `ccbr`/`CCBR` prefixes (with optional `_`/`-`)
  - accept any non-empty remainder (for example `CCBR-abcd` -> `abcd`)
- Added absolute-path normalization for `--folder` handling in `projark` (#46 @kopardev):
  - relative paths are resolved to absolute paths before use
  - trailing slash/non-trailing slash inputs are both supported
- Hardened tar command construction with shell-safe quoting for paths containing spaces/special characters.
- Added ISO 8601 timestamps to `projark` log lines. (#47, @kopardev)
- Added completion/failure email notifications for `projark` (#48, @kopardev):
  - recipient: `$USER@nih.gov`
  - sender: `NCICCBR@mail.nih.gov`
- Added Open OnDemand graphical session detection in runtime checks (future-facing; `projark` still runs only on Helix today).
- Updated README/MkDocs docs with:
  - new short-option usage examples
  - current `projectnumber` behavior
  - path normalization behavior
  - timestamped logging and notification behavior
  - Open OnDemand availability disclaimer (Biowulf-only today; not directly available on Helix)

## v3.0.0

- Replaced legacy bash `projark` workflow with a Python-native `projark` CLI (`deposit`, `retrieve`) integrated into the `parkit` package.
- Archived old bash implementation at `legacy/projark_legacy.sh`; `src/parkit/scripts/projark` now points to the Python CLI.
- Added `projark deposit` end-to-end archival flow with:
  - `checkapisync` preflight gate
  - Helix host enforcement
  - `tmux`/`screen` session enforcement
  - project/datatype normalization
  - scratch staging, tar/filelist generation, md5 generation
  - transfer via `dm_register_directory`
  - cleanup enabled by default (`--no-cleanup` to retain artifacts)
- Added configurable tar split threshold/chunk size for deposit: `--split-size-gb` (default `500` GB).
- Added human-readable tar size reporting (MB/GB/TB + bytes) in `projark` output.
- Added `projark retrieve` enhancements:
  - selected-file retrieval with `--filenames`
  - full-collection retrieval when `--filenames` is omitted (`dm_download_collection`)
  - `--unsplit`/`--unspilt` merge support for multiple split tar groups
- Improved `projark` CLI output with stepwise status messages and consistent step numbering.
- Added subcommand version support:
  - `projark --version`
  - `projark deposit --version`
  - `projark retrieve --version`
  - all return the same package-aware message
- Suppressed bootstrap Java/environment warnings for version-only invocations.
- Updated `checkapisync` logic to treat merge-history-only divergence as in-sync when local/upstream trees match.
- Reworked docs to versioned MkDocs structure with `projark`-first workflows and updated operational guidance.
- Updated docs/README guidance:
  - use `mamba activate ...` directly
  - initialize mamba only if not already in `PATH`
  - reference HPC_DME setup guide
  - document minimum Java requirement: `HPC_DM_JAVA_VERSION >= 23`
  - standardize guidance to run all operations in `tmux`/`screen`
- Documentation: Improved code example readability in README. (#34, @kelly-sovacool)

## v2.2.0

- Feature: Automatic object name resolution (fix #30)
  - Added logic to detect and resolve naming conflicts by appending \_002, \_003, etc. to object names during deposit.
  - Metadata .json and .filelist files are updated accordingly to reflect new names.
- Enhancement: Java version management (fix #31)
  - Introduced support for setting HPC_DM_JAVA_VERSION dynamically with a default fallback to 23.0.2 on Biowulf/Helix
- Fixed ccr partition issue (fix #32)

## v2.1.3

- fix scontrol issue on HELIX

## v2.1.1

### Features/BugFixes

- fix loading `parkit_dev` conda env (#26)

## v2.1.0

### Features/BugFixes

- adding `collectiontype` to `createmetadata` command
- excluding `*.tar.filelist` from `--cleanup` as it may need be put alongside README
- create readme with `--makereadme` argument
- `projark` subcommand for easy CCBR project backup

## v2.0.1

### Features/BugFixes

- package renamed from `parkit_pkg` to `parkit`
- reorganized package by recreating `src` folder

## v2.0.0

### Features/BugFixes

- converted to python package (fix #4)

## v1.0.1

### Features/BugFixes

- `parkit_tarball2hpcdme` added to start with tarballs
- `update_collection_metadata.py` added to add more information from AMP dump

## v1.0

### Features/BugFixes

- `parkit` added... built using python
- `parkit_e2e` added ... uses `parkit` and "slurm"
