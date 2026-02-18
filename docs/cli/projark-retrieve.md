# projark retrieve

Retrieves archived files from:

`/CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>`

## Syntax

Selected files:

```bash
projark retrieve \
  --projectnumber 12345 \
  --datatype Analysis \
  --filenames new.tar_0001,new.tar_0002 \
  --unsplit
```

Full collection:

```bash
projark retrieve --projectnumber 12345 --unsplit
```

## Inputs

- `--projectnumber` (required)
- `--datatype` (optional, default `Analysis`)
- `--folder` (optional): local base folder (default `/scratch/$USER/CCBR-<projectnumber>`)
- `--filenames` (optional): comma-separated object names; omit for full collection download
- `--unsplit` / `--unspilt`: merge split tar parts after download

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check
3. `tmux`/`screen` session check
4. Validate source collection exists
5. Download selected objects (`dm_download_dataobject`) or full collection (`dm_download_collection`)
6. Optionally merge `*.tar_0001`, `*.tar_0002`, ... into tar files

## Merge Behavior

`--unsplit` supports multiple split groups in one run.
