# projark retrieve

Retrieves archived files from:

`/CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>`

## Syntax

Selected files:

```bash
projark retrieve \
  -p CCBR-12345 \
  -d Analysis \
  -n new.tar_0001,new.tar_0002 \
  -u
```

Full collection:

```bash
projark retrieve -p 12345 -u
```

Download under a different staging base:

```bash
projark retrieve -p 12345 -u --staging-dir /data/$USER/staging
```

## Inputs

- `-p`, `--projectnumber`, `--project-number` (required)
- `-d`, `--datatype` (optional, default `Analysis`)
- `-f`, `--folder` (optional): local base folder (default `<staging base>/CCBR-<projectnumber>`)
- `--staging-dir` (optional): staging base; files are downloaded to `<staging-dir>/CCBR-<projectnumber>/<datatype>/`. Mutually exclusive with `--folder`.
- `-n`, `--filenames` (optional): comma-separated object names; omit for full collection download
- `-u`, `--unsplit` / `--unspilt`: merge split tar parts after download

`--projectnumber` normalization:

- Accepts any non-empty value.
- Repeated leading `ccbr` prefixes are removed (case-insensitive; each may be followed by `_`, `-`, or nothing).

Download location (first match wins):

1. `--folder DIR` -> `DIR`
2. `--staging-dir DIR` -> `DIR/CCBR-<projectnumber>`
3. `$PROJARK_STAGING_DIR` -> `$PROJARK_STAGING_DIR/CCBR-<projectnumber>`
4. `/scratch/$USER/CCBR-<projectnumber>`

Files are placed in `<base>/<datatype>/`. `retrieve` never writes the `.projark_staging` marker, and it refuses to download into a folder that has one, or into any folder inside it (a leftover `deposit` staging folder, e.g. after `-k` or a failed deposit), because a later `projark deposit` would delete it. Remove the leftover folder or choose another `--folder`/`--staging-dir`. This applies however the target was chosen.

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check
3. `tmux`/`screen`/Open OnDemand graphical session check
4. Validate source collection exists
5. Fetch full object listing via a single `dm_query_dataobject` call; validate all `--filenames` entries against the in-memory result set
6. Print advisory if split tar parts (`*.tar_NNNN`) are detected and `--unsplit` was not passed
7. Free-space preflight on the download folder (see [Free-Space Check](#free-space-check))
8. Download selected objects (`dm_download_dataobject`) or full collection (`dm_download_collection`)
9. Optionally merge `*.tar_0001`, `*.tar_0002`, ... into tar files

## Free-Space Check

Before downloading, `retrieve` aborts if the target filesystem has less free space than:

- the total size of the selected objects (all objects when `--filenames` is omitted);
- plus, with `--unsplit`, the size of each split group again, because the merged tar is written while the parts still exist;
- plus a margin of 1 GiB or 1% of the total, whichever is larger.

Per-user/group quotas are not visible to this check; use `checkquota` on Biowulf/Helix.

## Merge Behavior

`--unsplit` supports multiple split groups in one run.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

`--folder FASTQ` and `--folder FASTQ/` are both valid for directories.
Relative folder paths are converted to absolute paths before use.
`projark` sends completion/failure email to `$USER@nih.gov` from `NCICCBR@mail.nih.gov`.
