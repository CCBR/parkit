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

- Requested objects are downloaded to `/scratch/$USER/CCBR-12345/Analysis` (or custom `--folder`).
- If `--unsplit` is used, matching split tar parts are merged.
