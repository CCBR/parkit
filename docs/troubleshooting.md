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

If prompted to use a session wrapper, start `tmux`/`screen` (or use an Open OnDemand graphical session) and rerun.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

## Token/Auth Failures

If token generation fails during `syncapi`, verify credentials and inspect:

`HPC_DME_APIs/utils/temp/log`

## Missing Collection/Object on Retrieve

- Validate project number and datatype.
- Use `--filenames` only for exact object names.
- Omit `--filenames` for full collection retrieval.

## Split Merge Expectations

`--unsplit` merges only files matching `*.tar_0001`, `*.tar_0002`, etc. If none are present, merge is skipped.

## Ghost Records After a Partial Deposit

If a prior deposit failed mid-transfer, HPC-DME may have created catalog records for some files without any associated data ("ghost records"). A subsequent deposit attempt will fail with:

```
Detected data object record without system metadata <path>
```

Delete the ghost records before retrying:

```bash
dm_delete_dataobject /CCBR_Archive/GRIDFTP/Project_CCBR-1128/Analysis/ccbr1128.tar.filelist
dm_delete_dataobject /CCBR_Archive/GRIDFTP/Project_CCBR-1128/Analysis/ccbr1128.tar.filelist.md5
dm_delete_dataobject /CCBR_Archive/GRIDFTP/Project_CCBR-1128/Analysis/ccbr1128.tar.md5
```

Then rerun `projark deposit`.

## Proxy Settings Error

If `projark deposit` aborts with:

```
Active proxy settings found in hpcdme.properties
```

Open `$HPC_DM_UTILS/hpcdme.properties` and comment out any active `hpc.server.proxy.url` or `hpc.server.proxy.port` lines by prefixing them with `#`. Then retry.

## `projark ls` Shows No Results After Deposit

The HPC-DME search index lags up to **60 minutes** behind recent deposits. Wait and retry:

```bash
projark ls <projectnumber>
```
