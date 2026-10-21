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

## Staging Folder Exists but Was Not Created by projark

**Symptom:** `projark deposit` aborts saying `<base>/CCBR-<projectnumber>` exists but was not created by `projark deposit`.

**Cause:** `deposit` only deletes a staging folder that contains its `.projark_staging` marker. Folders left by older `parkit` versions (e.g. after `-k`/`--no-cleanup`), folders created by `projark retrieve`, or unrelated folders have no marker.

**Fix:** nothing has been created in HPC-DME yet. Check the folder contents, then either:

- remove it, e.g. `rm -rf /scratch/$USER/CCBR-<projectnumber>`;
- rename it; or
- rerun with a different `--staging-dir`.

## Retrieve Refuses a Leftover Staging Folder

**Symptom:** `projark retrieve` aborts because the download folder, or a folder above it, contains a `.projark_staging` marker.

**Cause:** the folder is a leftover `deposit` staging folder (e.g. after `-k`/`--no-cleanup` or a failed deposit). A later `deposit` would delete it, including anything downloaded into it.

**Fix:** check its contents and remove the leftover folder (e.g. `rm -rf /scratch/$USER/CCBR-<projectnumber>`), or rerun with another `--folder` or `--staging-dir`.

## Not Enough Free Space for Staging/Download

**Symptom:** `projark deposit` or `projark retrieve` aborts with a free-space error listing the required and available space and the path.

**Cause:** the staging/download filesystem cannot hold the estimated peak usage. For `deposit` this is about 2x the tar size when the tar will be split, otherwise 1x, plus the `.filelist` and a margin; space used by a marked staging folder from a previous run counts as reclaimable. For `retrieve` it is the download size, plus the split groups again with `--unsplit`.

**Fix:**

- Stage on a larger filesystem with `--staging-dir` (or `PROJARK_STAGING_DIR`), e.g. `/data/$USER/staging` or a group data area. For `retrieve`, `--folder` also works.
- Free space on the target filesystem.
- Check quotas with `checkquota`: the preflight sees filesystem free space only, so a per-user/group quota can still be exceeded ("Disk quota exceeded").
- Lowering `--split-size-gb` does not help: once the tar is split, the full tar and its parts coexist, so the peak stays about 2x the tar size.

## No Space Left on Device During Split

**Symptom:** an older `projark deposit` created the tar but `split` failed with `No space left on device`.

**Cause:** `split` writes the parts while the full tar still exists, so peak usage is about 2x the tar size. Older versions had no free-space check and always staged in `/scratch/$USER`.

**Fix:** upgrade `parkit`; `deposit` now checks free space before creating HPC-DME collections. Remove the leftover `/scratch/$USER/CCBR-<projectnumber>` folder (it has no marker, so `deposit` will refuse to reuse it) and rerun with `--staging-dir` on a filesystem with enough space. If HPC-DME records were created by the failed run, see [Ghost Records After a Partial Deposit](#ghost-records-after-a-partial-deposit).

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
