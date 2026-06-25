# projark ls

Lists all data objects archived under a project's HPC-DME vault collection and renders them as a human-readable tree with file sizes, depositor name, and deposit date.

## Syntax

```bash
projark ls <PROJECTNUMBER>
projark ls <PROJECTNUMBER> --json
```

## Inputs

| Argument | Type | Description |
|----------|------|-------------|
| `PROJECTNUMBER` | positional (required) | Project number — same formats accepted as `deposit`/`retrieve` |
| `--json` | flag | Emit results as a JSON array instead of the tree view |

### Project number formats

All of the following are equivalent:

```bash
projark ls 982
projark ls ccbr982
projark ls CCBR-982
projark ls CCBR_982
```

## Output

### Default (tree view)

```
Project_CCBR-982  (1.01 TB)
├── Analysis/  (569.84 GB)
│   ├── ccbr982.tar_0001                              500.00 GB     Vishal Koparde,260625
│   └── ccbr982.tar_0002                              69.84 GB      Vishal Koparde,260625
└── Rawdata/  (465.57 GB)
    └── ccbr982.tar                                   465.57 GB     Vishal Koparde,240429
```

Each file row shows: filename, size, depositor (display name), deposit date (YYMMDD).

### JSON output (`--json`)

```bash
projark ls 982 --json
```

Emits a JSON array:

```json
[
  {
    "path": "/CCBR_Archive/GRIDFTP/Project_CCBR-982/Analysis/ccbr982.tar_0001",
    "size_bytes": 536870912000,
    "size_human": "500.00 GB",
    "depositor": "Vishal Koparde",
    "deposit_date": "260625"
  }
]
```

## Notes

- No Helix host check, no tmux/screen requirement, no sync-gate check — `ls` is read-only.
- Does **not** send a completion email.
- Newly deposited files may not appear for up to **60 minutes** due to DME search index lag.
- Queries use `dm_query_dataobject` — a single paginated API call regardless of how many objects exist.
