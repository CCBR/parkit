# projark Overview

`projark` is the recommended high-level interface for project archival.

## Version

```bash
projark --version
projark deposit --version
projark retrieve --version
```

All print the same package-aware message.

## Subcommands

- `deposit`: archive local folder content to HPC-DME project collection.
- `retrieve`: retrieve archived data objects back to local scratch.

## Safety Gates

Both subcommands run preflight checks:

- `parkit checkapisync`
- host must be `helix.nih.gov`
- session must be inside `tmux`, `screen`, or an Open OnDemand graphical session
- Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

## Logging and Notification

- `projark` logs include ISO 8601 timestamps.
- On completion/failure, `projark` sends an email notification to `$USER@nih.gov`.
- Notification sender is `NCICCBR@mail.nih.gov`.
