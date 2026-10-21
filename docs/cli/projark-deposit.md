# projark deposit

Archives a local project folder into HPC-DME collection paths under:

`/CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>`

## Syntax

```bash
projark deposit \
  -f /data/CCBR/projects/CCBR-12345 \
  -p CCBR-12345 \
  -d Analysis
```

Stage on a larger filesystem instead of `/scratch/$USER`:

```bash
projark deposit \
  -f /data/CCBR/projects/CCBR-12345 \
  -p CCBR-12345 \
  -d Analysis \
  --staging-dir /data/$USER/staging

# or set it once for the session
export PROJARK_STAGING_DIR=/data/$USER/staging
```

## Inputs

- `-f`, `--folder` (required): local folder to archive.
- `-p`, `--projectnumber`, `--project-number` (required): project identifier.
- `-d`, `--datatype` (optional): `Analysis` (default) or `Rawdata` (case-insensitive).
- `-t`, `--tarname` (optional): override tar filename (default `ccbr<projectnumber>.tar`).
- `-s`, `--split-size-gb` (optional): split threshold/chunk size, default `500`.
- `--staging-dir` (optional): base folder for staging (default `$PROJARK_STAGING_DIR`, else `/scratch/$USER`). Files are written to `<staging-dir>/CCBR-<projectnumber>/<datatype>/`. A custom folder must already exist and be writable.
- `--cleanup` / `-k`, `--no-cleanup`: delete the staging folder after a successful transfer; cleanup is enabled by default.

`--projectnumber` normalization:

- Accepts any non-empty value.
- Repeated leading `ccbr` prefixes are removed (case-insensitive; each may be followed by `_`, `-`, or nothing).
- Examples:
  - `CCBR-1234` -> `1234`
  - `CCBR-abcd` -> `abcd`
  - `ccbr_ccbr-1234abc` -> `1234abc`

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check; print active `hpcdme.properties` lines for verification; abort if proxy settings are active
3. `tmux`/`screen`/Open OnDemand graphical session check
4. Staging preflight, local only and before anything is created in HPC-DME (see [Staging Preflight](#staging-preflight))
5. Ensure target collections exist (create as needed with all required HPC-DME metadata)
6. Recreate the staging folder, write the `.projark_staging` marker, and stage tar + filelist in `<base>/CCBR-<projectnumber>/<datatype>/`
7. Split tar if above split threshold
8. Generate `.md5` for staged files
9. Check staged files against destination vault; rename with counter if conflict found
10. Transfer the `<datatype>/` folder via `dm_register_directory` (hidden/dot files automatically excluded)
11. Cleanup the staging folder (default on; only if it carries the `.projark_staging` marker)

## Staging Preflight

Before any HPC-DME collection is created, `deposit`:

- resolves the staging base (`--staging-dir` > `$PROJARK_STAGING_DIR` > `/scratch/$USER`);
- checks that `--tarname` is a plain file name;
- aborts if the staging folder `<base>/CCBR-<projectnumber>` is the source folder, is inside it, or contains it;
- estimates the uncompressed tar size from the source tree and aborts if free space is insufficient (see [Free-Space Check](#free-space-check));
- aborts if `<base>/CCBR-<projectnumber>` already exists without a `.projark_staging` marker (see [Staging Folder Marker](#staging-folder-marker)).

## Staging Folder Marker

`deposit` writes `<base>/CCBR-<projectnumber>/.projark_staging` (JSON with `created_at`, `user`, `host`, `parkit_version`, `projectnumber`, `datatype`, `source`). The marker sits outside the uploaded `<datatype>/` folder, so it is never sent to HPC-DME.

- An existing `CCBR-<projectnumber>` folder is deleted and recreated only if it has the marker, including under `/scratch/$USER`.
- An existing folder without the marker makes `deposit` abort without touching it. Remove or rename it (after checking its contents), or choose another `--staging-dir`.
- Cleanup also requires the marker.
- Folders left by older `parkit` versions (e.g. after `-k`) have no marker and must be removed manually.

## Free-Space Check

`deposit` estimates the uncompressed tar size from the source tree (file sizes plus tar headers and padding) and requires, on the staging filesystem:

- about **2x** the tar size if the tar will exceed `--split-size-gb`, because `split` writes the parts while the full tar still exists;
- otherwise **1x** the tar size;
- plus the estimated `.filelist` size (one line per archived entry; can be large for many small files);
- plus a margin of 1 GiB or 1% of the tar size, whichever is larger.

Space used by an existing marked staging folder from a previous run (e.g. after `-k` or a failed deposit) counts as available, because it is deleted before staging starts.

The check reads filesystem free space and cannot see per-user or per-group quotas (e.g. `/data/$USER`, `/data/CCBR`). Check your quota with `checkquota` on Biowulf/Helix before staging on a quota-limited area.

## Notes

- Run from `tmux`, `screen`, or an Open OnDemand graphical session.
- Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.
- `--folder FASTQ` and `--folder FASTQ/` are both valid for directories.
- Relative folder paths are converted to absolute paths before use.
- For raw data, pass `--datatype rawdata`.
- `projark` sends completion/failure email to `$USER@nih.gov` from `NCICCBR@mail.nih.gov`.
- **Proxy settings** (`hpc.server.proxy.url`, `hpc.server.proxy.port`) must be commented out in `hpcdme.properties`. Deposit aborts with a descriptive error if active proxy lines are found.
- **Conflict handling**: if a staged file already exists in the destination collection, the staged files are renamed by inserting a zero-padded counter before the first extension (e.g. `ccbr1431.tar` → `ccbr1431_001.tar`).
- **Split-tar conflict detection**: checks for both the base tarball name and the first split-chunk suffix (`*.tar_0001`) to detect prior split deposits.
- **Hidden files** (filenames starting with `.`) are automatically excluded from `dm_register_directory`.
