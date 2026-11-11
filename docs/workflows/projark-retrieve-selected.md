# projark Retrieve Selected Files

Retrieve specific objects by name.

## Example

```bash
projark retrieve \
  --projectnumber 12345 \
  --datatype Analysis \
  --filenames new.tar_0001,new.tar_0002,new.tar.filelist \
  --unsplit
```

## Result

- Requested objects are downloaded to `<staging base>/CCBR-12345/Analysis` (staging base: `--staging-dir`, else `$PROJARK_STAGING_DIR`, else `/scratch/$USER`), or to `<folder>/Analysis` with `--folder`.
- Aborts before downloading if the target filesystem lacks space for the requested objects (plus the merged tars with `--unsplit`).
- If `--unsplit` is used, matching split tar parts are merged.
