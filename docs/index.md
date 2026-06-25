# parkit Documentation

`parkit` is a CLI toolkit for archiving CCBR project data to HPC-DME (`/CCBR_Archive/GRIDFTP/...`).

For most users, the recommended interface is `projark`, which provides guided `deposit` and `retrieve` workflows for entire CCBR project folder(s).

## In This Version (`v3.1.0`)

- `projark ls <projectnumber>` — list vault contents as a tree with sizes, depositor, and deposit date.
- `parkit ls <collection-path>` — list any HPC-DME collection path.
- `projark deposit` HTTP 400 fix: all required HPC-DME metadata fields now sent on collection creation.
- Split-tar conflict detection: prior split deposits correctly detected before re-depositing.
- Temp file isolation: HPC-DME CLI response files no longer accumulate in the working directory.
- Pre-transfer conflict detection and automatic file renaming in `projark deposit`.
- Proxy settings validation: aborts if proxy lines are active in `hpcdme.properties`.
- Batch existence check in `projark retrieve`; split-tar advisory when `--unsplit` not passed.

## Quick Start

```bash
projark --version
projark deposit --help
projark retrieve --help
projark ls --help
```

## Recommended Path

1. Complete environment setup from [Getting Started](getting-started.md).
2. Use [projark Deposit (Recommended)](workflows/projark-deposit-workflow.md) to archive data.
3. Use [projark Retrieve](workflows/projark-retrieve-selected.md) when you need data back.

## Notes

- `projark` is intended for Helix (`helix.nih.gov`).
- All runs should be executed in `tmux`, `screen`, or an Open OnDemand graphical session.
- Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.
- `projark` logs include ISO 8601 timestamps.
- `projark` sends completion/failure email to `$USER@nih.gov` from `NCICCBR@mail.nih.gov`.
- Docs are versioned; this set describes `v3.1.0` behavior.
