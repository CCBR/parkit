# projark Retrieve Full Collection

When `--filenames` is omitted, `projark` downloads the entire datatype collection.

## Example

```bash
projark retrieve --projectnumber 12345 --datatype Analysis --unsplit
```

## Behavior

- Uses `dm_download_collection <source-collection> <base-local-folder>`.
- Collection lands at `/scratch/$USER/CCBR-12345/Analysis` by default.
- `--unsplit` then scans that datatype folder and merges all split tar groups.
