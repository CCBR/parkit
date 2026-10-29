## parkit development version

- `projark ls` and `parkit ls` now show exact bytes by default. Add `--human-readable` for decimal KB/MB/GB; JSON retains `size_bytes` and uses decimal `size_human`. (#78, @kopardev)

## parkit 3.3.0

- Fixed the docs home page showing a stale "In This Version (`v3.1.0`)" in every versioned build; it now has a version-neutral "What's New" section. Added the v3.2.0 release notes page. (#74, @kopardev)
- Refreshed the `parkit --help` output in `README.md` (adds `ls`, `-v/--version`, and the new `checkapisync`/`syncapi` descriptions) and listed `ls` in the `parkit` CLI overview docs. (#71, @kopardev)
- `projark` staging location is now configurable, with safety checks to avoid failures like `split` running out of space in `/scratch/$USER` (#72, #73, @kopardev):
  - New `--staging-dir DIR` option (and `PROJARK_STAGING_DIR` env var) for `projark deposit` and `projark retrieve`; the default remains `/scratch/$USER`. Files go in `<DIR>/CCBR-<projectnumber>/<datatype>/`. For `retrieve`, `--staging-dir` and `-f/--folder` are mutually exclusive.
  - `projark deposit` estimates the tar size and aborts before creating any HPC-DME collection if the staging filesystem lacks free space (about 2x the tar size when it will be split, else 1x, plus the `.filelist` and a margin). `projark retrieve` checks free space before downloading (including merged tars with `--unsplit`).
  - `projark deposit` aborts if the staging folder is the source folder, is inside it, or contains it.
  - `projark deposit` writes a `.projark_staging` marker in `<DIR>/CCBR-<projectnumber>/` and only deletes (on rerun or cleanup) staging folders that carry it. The free-space check counts an existing marked staging folder from a previous run as reclaimable, since it is deleted before staging.
  - `projark retrieve` never writes the marker and refuses to download into a folder that has one, or into any folder inside it (a leftover deposit staging folder), since a later `deposit` would delete it.
  - **Behavior change:** an existing unmarked `/scratch/$USER/CCBR-<projectnumber>` (e.g. left by an older version with `-k`) now makes `deposit` abort instead of being silently deleted; check and remove it manually.
  - The free-space check cannot see per-user/group quotas (e.g. `/data/$USER`, `/data/CCBR`); use `checkquota`.

## parkit 3.2.0

- `parkit syncapi` and `parkit checkapisync` now track HPC_DME_APIs releases, which are published as `releases/X.Y.Z` branches instead of GitHub tags/releases (#68, #69, @kopardev):
  - The default target is the latest stable release: the highest-numbered `releases/X.Y.Z` branch merged into `master`, compared numerically. Malformed names (e.g. `releases/1.5.2-candidate`) are ignored.
  - New `--ref` option (and `HPC_DME_APIs_REF` env var, also used by the `projark` sync check) to target a specific tag or branch; `X.Y.Z` is shorthand for `releases/X.Y.Z`.
  - `syncapi` switches to the target branch (or tag) instead of running `git pull`, never creates merge commits, never downgrades automatically, and aborts on uncommitted tracked changes or local-only commits.
  - `checkapisync` reports the local and target release and no longer reports a clone stuck on an old release branch as in sync.
  - Both commands now return meaningful exit codes (`0` ok, `1` out of sync/failure, `2` configuration error).
- Removed the hard-coded personal fallback path for the HPC_DME_APIs repository; set `HPC_DM_UTILS`, `HPC_DME_APIs`, or pass `--repo`. (#68, #69, @kopardev)
- Fixed the `mamba activate` path in `README.md` and the Getting Started docs to point to the current `parkit_3` environment. (#67, @kopardev)

## v3.1.0

- Added `projark ls <projectnumber>` subcommand to list all data objects in a project's HPC-DME vault collection as a tree with human-readable sizes, depositor name, and deposit date (#62, @kopardev):
  - Uses a single `dm_query_dataobject` call (no extra API calls for per-file metadata).
  - Groups objects by sub-collection (`Analysis/`, `Rawdata/`) with sub-collection size totals.
  - Each file row shows: filename, size, depositor (`registered_by_name`), deposit date (`data_transfer_completed`, formatted as `YYMMDD`).
  - Accepts the same project number formats as `deposit`/`retrieve` (e.g. `projark ls 982`, `projark ls ccbr982`, `projark ls CCBR-982`).
  - No Helix, tmux, or sync-gate checks required (read-only operation).
  - Prints a note that newly deposited files may not appear for up to 60 minutes (DME search index lag).
  - Does not send a completion email.
- Added `parkit ls <COLLECTION_PATH>` subcommand to list data objects under any HPC-DME collection path (e.g. `parkit ls /CCBR_Archive/GRIDFTP/Project_CCBR-982`), sharing its listing backend with `projark ls`. (#62, @kopardev)
- Added `--json` flag to `parkit ls` and `projark ls` to emit results as a JSON array instead of the tree view. (#62, @kopardev)
- Fixed the `ls` tree view to render the full collection hierarchy at any depth, so listings such as `parkit ls /CCBR_Archive/GRIDFTP` no longer collapse intermediate `Project_CCBR-*` folders into duplicated `Analysis/`/`Rawdata/` labels. (#62, @kopardev)
- Fixed `projark retrieve` step messages that printed `--unspilt` instead of `--unsplit`. (#62, @kopardev)
- Fixed `projark deposit` name-conflict detection to also check for the first split-chunk suffix (`*.tar_0001`) when testing whether a base tar name is already taken in HPC-DME. Previously, a project whose tarball was split on a prior deposit (producing `ccbr982.tar_0001`, `ccbr982.tar_0002`, …) would not be detected as a conflict because the base name `ccbr982.tar` never exists as a data object. (#61, @kopardev)
- Improved `projark retrieve` (#62, @kopardev):
  - Replaced N serial `dm_get_dataobject` existence checks (one per `--filenames` entry) with a single `dm_query_dataobject` call; all requested filenames are validated against the returned in-memory name set.
  - After fetching the object listing, automatically detects split tar parts (`*.tar_NNNN`) in the collection and prints an advisory message if `--unsplit` was not passed.
- Fixed HPC-DME CLI `*.tmp` response files (e.g. `collection-registration-response-message.json.tmp`, `get-item-response-header.tmp`) accumulating in the user's working directory after every `projark` run. `run_dm_cmd` now executes each `dm_*` subprocess inside a per-call `tempfile.TemporaryDirectory` named `parkit_<username>_<random>/`, so all temp files are isolated and automatically deleted on return. This also prevents concurrent runs by the same or different users from overwriting each other's temp files. (#60, @kopardev)
- Fixed `projark deposit` HTTP 400 errors from HPC-DME when creating Project and Analysis/Rawdata collections (#53, @kopardev):
  - `_register_collection` now accepts `extra_metadata` to send all required DME fields.
  - Project collections are registered with: `project_title`, `project_description`, `origin`, `method`, `access`, `organism`, `summary_of_samples`, `project_start_date`.
  - Analysis/Rawdata sub-collections are registered with: `project_start_date`, `method`, `number_of_cases`.
  - `Rawdata` datatype is mapped to DME `collection_type` value `Analysis` (valid values: `Project`, `PI_Lab`, `Sample`, `Analysis`).
- After Step 2 in `projark deposit`, print the active (non-comment) lines from `$HPC_DM_UTILS/hpcdme.properties` with a 4-space indent so users can verify their HPC-DME configuration before the transfer begins. (#56, @kopardev)
- After Step 2 in `projark deposit`, check that proxy settings (`hpc.server.proxy.url`, `hpc.server.proxy.port`) are commented out in `hpcdme.properties`; abort with a descriptive error if any are active. Per HPC-DME team guidance (Udit Sehgal), proxy lines must not be set. (#57, @kopardev)
- Exclude dot files (filenames starting with `.`) from `dm_register_directory` during deposit by passing a temp exclude file with patterns `.*` and `**/.*` via the `-e` flag. Prevents hidden files such as shell per-directory history files from being registered to HPC-DME. (#58, @kopardev)
- Fixed the documentation site version selector by deploying versioned docs with `mike`, and added the parkit favicon and logo. (#51, @kopardev)
- Before `dm_register_directory`, check whether any staged file already exists in the destination HPC-DME collection; if so, rename all staged files (primary and `.md5`) by inserting a zero-padded counter before the first extension (e.g. `ccbr1431.tar` → `ccbr1431_001.tar`), using the lowest available counter so previous deposits are never overwritten. (#59, @kopardev)

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
