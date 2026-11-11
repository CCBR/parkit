# Operational Guidance

## Session Requirement

Run all operations in resilient sessions:

```bash
tmux new -s parkit
# or
screen -S parkit
```

Open OnDemand graphical sessions are also accepted.
`projark` enforces this for both `deposit` and `retrieve`.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

## Staging Location

`projark deposit` builds the tar, `.filelist`, split parts (`*.tar_NNNN`) and `.md5` files in a staging folder; `projark retrieve` downloads into the same location by default.

Staging base (first match wins):

1. `--staging-dir DIR`
2. `$PROJARK_STAGING_DIR`
3. `/scratch/$USER` (default)

For `retrieve`, `-f/--folder` overrides all of these (and cannot be combined with `--staging-dir`). A custom staging base must already exist and be writable.

Layout:

```
<base>/CCBR-<projectnumber>/
├── .projark_staging      # marker written by deposit (not uploaded)
└── <datatype>/           # Analysis or Rawdata; this folder is uploaded
    ├── ccbr<projectnumber>.tar (or .tar_0001, .tar_0002, ...)
    ├── ccbr<projectnumber>.tar.filelist
    └── *.md5
```

To stage on a larger filesystem for a whole session:

```bash
export PROJARK_STAGING_DIR=/data/$USER/staging
```

### Staging Marker

`deposit` writes a `.projark_staging` JSON marker (`created_at`, `user`, `host`, `parkit_version`, `projectnumber`, `datatype`, `source`) in `<base>/CCBR-<projectnumber>/`.

- An existing staging folder is deleted and recreated only if it has the marker (also under `/scratch/$USER`). Otherwise `deposit` aborts and asks you to remove/rename it or choose another `--staging-dir`.
- Cleanup also requires the marker.
- `retrieve` never writes the marker, and it refuses to download into a folder that has one, or into any folder inside it (a leftover deposit staging folder, e.g. after `-k` or a failed deposit), because a later `deposit` would delete it. Remove the leftover folder or choose another `--folder`/`--staging-dir`.
- `deposit` aborts if the staging folder is the source folder, is inside it, or contains it.

### Free-Space Check

Before creating any HPC-DME collection, `deposit` estimates the uncompressed tar size from the source tree (file sizes plus tar headers/padding) and aborts unless the staging filesystem has:

- about **2x** the tar size when the tar will exceed `--split-size-gb` (`split` writes the parts while the full tar still exists), otherwise **1x**;
- plus the estimated `.filelist` size (one line per archived entry; can be large for many small files);
- plus a margin of 1 GiB or 1% of the tar size, whichever is larger.

Space used by an existing marked staging folder from a previous run (e.g. after `-k` or a failed deposit) counts as available, because it is deleted before staging starts.

Before downloading, `retrieve` requires the size of the selected objects (all objects for a full collection), plus each split group's size again with `--unsplit` (the merged tar is written while the parts exist), plus the same margin.

The check uses filesystem free space only. Per-user/group quotas (e.g. `/data/$USER`, `/data/CCBR`) are not visible, so a quota can still be exceeded; check with `checkquota` on Biowulf/Helix.

## Split Threshold

`projark deposit` supports configurable split threshold/chunk size:

```bash
projark deposit ... --split-size-gb 500
```

Default is `500` GB.

## Cleanup Policy

- Default: the staging folder is deleted after a successful deposit (only if it carries the `.projark_staging` marker).
- To retain artifacts: `-k`/`--no-cleanup`. Remove the folder yourself afterwards, or the next `deposit` with the same staging base will reuse (wipe and recreate) it.

## Logging and Notifications

- `projark` logs include ISO 8601 timestamps.
- On completion/failure, `projark deposit` and `projark retrieve` send email to `$USER@nih.gov`.
- Notification sender is `NCICCBR@mail.nih.gov`.
- `projark ls` and `parkit ls` do not send email and require no session/gate checks.

## HPC-DME Configuration

- **Proxy settings** (`hpc.server.proxy.url`, `hpc.server.proxy.port`) must be **commented out** in `$HPC_DM_UTILS/hpcdme.properties`. `projark deposit` checks this and aborts with an error if active proxy lines are found.
- After the preflight checks, `projark deposit` prints the active lines from `hpcdme.properties` so you can verify configuration before the transfer begins.

## Dot-File Exclusion

Hidden files (filenames starting with `.`) are automatically excluded from `dm_register_directory` during deposit. This prevents shell per-directory history files and other hidden files from being registered to HPC-DME.

## Temp File Isolation

`dm_*` CLI commands produce response files (e.g. `*.tmp`) that are now isolated inside a per-call temporary directory and automatically deleted after each command. No temp files accumulate in your working directory.

## DME Search Index Lag

The HPC-DME search index used by `projark ls` and `parkit ls` can lag up to **60 minutes** behind a recent deposit. If newly deposited files do not appear in `ls` output, wait and retry.
