# parkit ls

Lists all data objects under any HPC-DME collection path and renders them as a tree with exact byte sizes. Uses the same backend as `projark ls` but accepts a full HPC-DME path instead of a project number.

## Syntax

```bash
parkit ls <COLLECTION_PATH>
parkit ls <COLLECTION_PATH> --human-readable
parkit ls <COLLECTION_PATH> --json
```

## Inputs

| Argument           | Type                  | Description                                           |
| ------------------ | --------------------- | ----------------------------------------------------- |
| `COLLECTION_PATH`  | positional (required) | Full HPC-DME collection path                          |
| `--human-readable` | flag                  | Show decimal KB, MB, GB instead of exact bytes        |
| `--json`           | flag                  | Emit results as a JSON array instead of the tree view |

## Examples

List a single project:

```bash
parkit ls /CCBR_Archive/GRIDFTP/Project_CCBR-982
```

List **all projects** under the GRIDFTP root (shows full multi-project hierarchy):

```bash
parkit ls /CCBR_Archive/GRIDFTP
```

## Size formatting

Sizes default to exact integer bytes (`B`) for files and collection totals.
Use `--human-readable` for decimal units with one digit after the decimal point: 1 KB = 1000 bytes, 1 MB = 1000000 bytes.
For example, `57743 B` becomes `57.7 KB`. This avoids the previous binary/decimal
unit mismatch with HPC-DME; displayed precision may still differ from the portal.
`--human-readable` and `--json` are mutually exclusive. JSON retains numeric
`size_bytes` and includes decimal `size_human`. Unknown sizes remain unknown.

## Output

### Default (tree view)

```
GRIDFTP  (2037000000000 B)
├── Project_CCBR-1068/  (1000000000000 B)
│   └── Analysis/  (1000000000000 B)
│       ├── ccbr1068.tar_0001                         500000000000 B     Samarth Mathur,260220
│       └── ccbr1068.tar_0002                         500000000000 B     Samarth Mathur,260220
└── Project_CCBR-982/  (1037000000000 B)
    ├── Analysis/  (571000000000 B)
    │   ├── ccbr982.tar_0001                          500000000000 B     Vishal Koparde,260625
    │   └── ccbr982.tar_0002                          71000000000 B      Vishal Koparde,260625
    └── Rawdata/  (466000000000 B)
        └── ccbr982.tar                               466000000000 B     Vishal Koparde,240429
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
    "size_bytes": 500000000000,
    "size_human": "500.0 GB",
    "depositor": "Vishal Koparde",
    "deposit_date": "260625"
  }
]
```

## Notes

- No Helix host check, no tmux/screen requirement, no sync-gate check.
- Newly deposited files may not appear for up to **60 minutes** due to DME search index lag.
- For project-level queries, prefer `projark ls <projectnumber>` which constructs the path automatically.
