# Troubleshooting

## Out of Sync Error

If Step 1 fails in `projark`, run:

```bash
parkit syncapi
```

Then rerun your `projark` command.

## Host Check Failure

`projark` requires Helix host identity (`helix.nih.gov`).

## Session Check Failure

If prompted to use `tmux`/`screen`, start one and rerun.

## Token/Auth Failures

If token generation fails during `syncapi`, verify credentials and inspect:

`HPC_DME_APIs/utils/temp/log`

## Missing Collection/Object on Retrieve

- Validate project number and datatype.
- Use `--filenames` only for exact object names.
- Omit `--filenames` for full collection retrieval.

## Split Merge Expectations

`--unsplit` merges only files matching `*.tar_0001`, `*.tar_0002`, etc. If none are present, merge is skipped.
