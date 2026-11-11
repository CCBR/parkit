# projark Retrieve Full Collection

When `--filenames` is omitted, `projark` downloads the entire datatype collection.

## Example

```bash
projark retrieve --projectnumber 12345 --datatype Analysis --unsplit
```

## Behavior

- Uses `dm_download_collection <source-collection> <base-local-folder>`.
- Collection lands at `<staging base>/CCBR-12345/Analysis`, where the staging base is `--staging-dir`, else `$PROJARK_STAGING_DIR`, else `/scratch/$USER` (or use `--folder` for an explicit base).
- Aborts before downloading if the target filesystem lacks space for the whole collection (plus the merged tars with `--unsplit`).
- `--unsplit` then scans that datatype folder and merges all split tar groups.
