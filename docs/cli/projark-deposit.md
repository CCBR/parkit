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

## Inputs

- `-f`, `--folder` (required): local folder to archive.
- `-p`, `--projectnumber`, `--project-number` (required): project identifier.
- `-d`, `--datatype` (optional): `Analysis` (default) or `Rawdata` (case-insensitive).
- `-t`, `--tarname` (optional): override tar filename (default `ccbr<projectnumber>.tar`).
- `-s`, `--split-size-gb` (optional): split threshold/chunk size, default `500`.
- `--cleanup` / `-k`, `--no-cleanup`: cleanup is enabled by default.

`--projectnumber` normalization:

- Accepts any non-empty value.
- Repeated leading `ccbr` prefixes are removed (case-insensitive; each may be followed by `_`, `-`, or nothing).
- Examples:
  - `CCBR-1234` -> `1234`
  - `CCBR-abcd` -> `abcd`
  - `ccbr_ccbr-1234abc` -> `1234abc`

## Runtime Behavior

1. Sync gate (`checkapisync`)
2. Helix host check
3. `tmux`/`screen`/Open OnDemand graphical session check
4. Ensure target collections exist (create as needed)
5. Stage tar + filelist in `/scratch/$USER/CCBR-<projectnumber>/<datatype>/`
6. Split tar if above split threshold
7. Generate `.md5` for staged files
8. Transfer via `dm_register_directory`
9. Cleanup scratch (default on)

## Notes

- Run from `tmux`, `screen`, or an Open OnDemand graphical session.
- Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.
- `--folder FASTQ` and `--folder FASTQ/` are both valid for directories.
- Relative folder paths are converted to absolute paths before use.
- For raw data, pass `--datatype rawdata`.
- `projark` sends completion/failure email to `$USER@nih.gov` from `NCICCBR@mail.nih.gov`.
