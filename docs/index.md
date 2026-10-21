# parkit Documentation

`parkit` is a CLI toolkit for archiving CCBR project data to HPC-DME (`/CCBR_Archive/GRIDFTP/...`).

For most users, the recommended interface is `projark`, which provides guided `deposit` and `retrieve` workflows for entire CCBR project folder(s).

## What's New

Use the version selector at the top of the page to view the docs for a specific release. Full details are in the [Release Notes](release-notes/v3.3.0.md) and the [CHANGELOG](https://github.com/CCBR/parkit/blob/main/CHANGELOG.md).

### v3.3.0

- `projark deposit` / `projark retrieve` `--staging-dir` (or `PROJARK_STAGING_DIR`): choose where tarballs, split parts and downloads are staged (default `/scratch/$USER`).
- Free-space preflight: `projark deposit` aborts before creating any HPC-DME collection if the staging filesystem cannot hold the tarball (about 2× when it will be split); `projark retrieve` checks space before downloading.
- Safer staging: only folders carrying a `.projark_staging` marker are ever deleted, and staging may not overlap the source folder. See [Operational Guidance](operations.md) and the [v3.3.0 release notes](release-notes/v3.3.0.md).

### v3.2.0

- `parkit syncapi` / `parkit checkapisync` track HPC_DME_APIs `releases/X.Y.Z` branches (latest stable release by default, or `--ref` / `HPC_DME_APIs_REF`) with meaningful exit codes. See [v3.2.0 release notes](release-notes/v3.2.0.md).
- Removed the hard-coded personal fallback path for the HPC_DME_APIs repository.

### v3.1.0

- `projark ls <projectnumber>` and `parkit ls <collection-path>` list vault contents.
- Several `projark deposit` / `retrieve` fixes. See [v3.1.0 release notes](release-notes/v3.1.0.md).

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
- Docs are versioned; use the version selector to match the docs to your installed `parkit` (`projark --version`).
