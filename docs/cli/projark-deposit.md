# projark deposit

Archives a local project folder into HPC-DME collection paths under:

`/CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>`

## Syntax

```bash
projark deposit \
  --folder /data/CCBR/projects/CCBR-12345 \
  --projectnumber 12345 \
  --datatype Analysis
```

## Inputs

- `--folder` (required): local folder to archive.
- `--projectnumber` (required): accepts `1234`, `ccbr1234`, `CCBR-1234`, `ccbr_1234`.
- `--datatype` (optional): `Analysis` (default) or `Rawdata` (case-insensitive).
- `--tarname` (optional): override tar filename (default `ccbr<projectnumber>.tar`).
- `--split-size-gb` (optional): split threshold/chunk size, default `500`.
- `--cleanup` / `--no-cleanup`: cleanup is enabled by default.

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check
3. `tmux`/`screen` session check
4. Ensure target collections exist (create as needed)
5. Stage tar + filelist in `/scratch/$USER/CCBR-<projectnumber>/<datatype>/`
6. Split tar if above split threshold
7. Generate `.md5` for staged files
8. Transfer via `dm_register_directory`
9. Cleanup scratch (default on)

## Notes

- Run from a `tmux` or `screen` session.
- For raw data, pass `--datatype rawdata`.
