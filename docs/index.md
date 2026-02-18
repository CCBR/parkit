# parkit Documentation

`parkit` is a CLI toolkit for archiving CCBR project data to HPC-DME (`/CCBR_Archive/GRIDFTP/...`).

For most users, the recommended interface is `projark`, which provides guided `deposit` and `retrieve` workflows for entire CCBR project folder(s).

## In This Version (`v3.0.0`)

- New Python-native `projark` command with structured subcommands.
- `projark deposit` for project archival with sync/host/session preflight checks.
- `projark retrieve` with selective file retrieval or full-collection retrieval.
- `--unsplit` support for merging downloaded split tar parts.
- Archived legacy bash `projark` workflow.

## Quick Start

```bash
projark --version
projark deposit --help
projark retrieve --help
```

## Recommended Path

1. Complete environment setup from [Getting Started](getting-started.md).
2. Use [projark Deposit (Recommended)](workflows/projark-deposit-workflow.md) to archive data.
3. Use [projark Retrieve](workflows/projark-retrieve-selected.md) when you need data back.

## Notes

- `projark` is intended for Helix (`helix.nih.gov`).
- All runs should be executed in `tmux` or `screen`.
- Docs are versioned; this set describes `v3.0.0` behavior.
