# projark ls

Lists all data objects archived under a project's HPC-DME vault collection and renders them as a tree with exact byte sizes with file sizes, depositor name, and deposit date.

## Syntax

```bash
projark ls <PROJECTNUMBER>
projark ls <PROJECTNUMBER> --human-readable
projark ls <PROJECTNUMBER> --json
```

## Inputs

| Argument           | Type                  | Description                                                    |
| ------------------ | --------------------- | -------------------------------------------------------------- |
| `PROJECTNUMBER`    | positional (required) | Project number — same formats accepted as `deposit`/`retrieve` |
| `--human-readable` | flag                  | Show decimal KB, MB, GB instead of exact bytes                 |
| `--json`           | flag                  | Emit results as a JSON array instead of the tree view          |

### Project number formats

All of the following are equivalent:

```bash
projark ls 982
projark ls ccbr982
projark ls CCBR-982
projark ls CCBR_982
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
Project_CCBR-982  (1037000000000 B)
├── Analysis/  (571000000000 B)
│   ├── ccbr982.tar_0001                              500000000000 B     Vishal Koparde,260625
│   └── ccbr982.tar_0002                              71000000000 B      Vishal Koparde,260625
└── Rawdata/  (466000000000 B)
    └── ccbr982.tar                                   466000000000 B     Vishal Koparde,240429
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
    "size_bytes": 500000000000,
    "size_human": "500.0 GB",
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
