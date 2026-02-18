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
- session must be inside `tmux` or `screen`
