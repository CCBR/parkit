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

## Inputs

- `-p`, `--projectnumber`, `--project-number` (required)
- `-d`, `--datatype` (optional, default `Analysis`)
- `-f`, `--folder` (optional): local base folder (default `/scratch/$USER/CCBR-<projectnumber>`)
- `-n`, `--filenames` (optional): comma-separated object names; omit for full collection download
- `-u`, `--unsplit` / `--unspilt`: merge split tar parts after download

`--projectnumber` normalization:

- Accepts any non-empty value.
- Repeated leading `ccbr` prefixes are removed (case-insensitive; each may be followed by `_`, `-`, or nothing).

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check
3. `tmux`/`screen`/Open OnDemand graphical session check
4. Validate source collection exists
5. Download selected objects (`dm_download_dataobject`) or full collection (`dm_download_collection`)
6. Optionally merge `*.tar_0001`, `*.tar_0002`, ... into tar files

## Merge Behavior

`--unsplit` supports multiple split groups in one run.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

`--folder FASTQ` and `--folder FASTQ/` are both valid for directories.
Relative folder paths are converted to absolute paths before use.
`projark` sends completion/failure email to `$USER@nih.gov` from `NCICCBR@mail.nih.gov`.
