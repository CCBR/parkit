# parkit ls

Lists all data objects under any HPC-DME collection path and renders them as a human-readable tree. Uses the same backend as `projark ls` but accepts a full HPC-DME path instead of a project number.

## Syntax

```bash
parkit ls <COLLECTION_PATH>
parkit ls <COLLECTION_PATH> --json
```

## Inputs

| Argument | Type | Description |
|----------|------|-------------|
| `COLLECTION_PATH` | positional (required) | Full HPC-DME collection path |
| `--json` | flag | Emit results as a JSON array instead of the tree view |

## Examples

List a single project:

```bash
parkit ls /CCBR_Archive/GRIDFTP/Project_CCBR-982
```

List **all projects** under the GRIDFTP root (shows full multi-project hierarchy):

```bash
parkit ls /CCBR_Archive/GRIDFTP
```

## Output

### Default (tree view)

```
GRIDFTP  (1.99 TB)
├── Project_CCBR-1068/  (1000.00 GB)
│   └── Analysis/  (1000.00 GB)
│       ├── ccbr1068.tar_0001                         500.00 GB     Samarth Mathur,260220
│       └── ccbr1068.tar_0002                         500.00 GB     Samarth Mathur,260220
└── Project_CCBR-982/  (1.01 TB)
    ├── Analysis/  (569.84 GB)
    │   ├── ccbr982.tar_0001                          500.00 GB     Vishal Koparde,260625
    │   └── ccbr982.tar_0002                          69.84 GB      Vishal Koparde,260625
    └── Rawdata/  (465.57 GB)
        └── ccbr982.tar                               465.57 GB     Vishal Koparde,240429
```

The tree renders the full path hierarchy at any depth. Sub-collection totals are shown in parentheses.

### JSON output (`--json`)

```bash
parkit ls /CCBR_Archive/GRIDFTP --json
```

Emits a JSON array of all data objects:

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

- No Helix host check, no tmux/screen requirement, no sync-gate check.
- Newly deposited files may not appear for up to **60 minutes** due to DME search index lag.
- For project-level queries, prefer `projark ls <projectnumber>` which constructs the path automatically.
