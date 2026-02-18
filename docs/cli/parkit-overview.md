# parkit Overview

`parkit` provides lower-level archival primitives.

## Command Group

```bash
parkit --help
```

Core subcommands:

- `createtar`
- `tarprep`
- `createemptycollection`
- `createmetadata`
- `deposittar`
- `checkapisync`
- `syncapi`

## When To Use `parkit` Directly

- You need manual control of each archival step.
- You are debugging individual data-management operations.
- You are operating legacy workflows.

For routine project archival/retrieval, use `projark`.
