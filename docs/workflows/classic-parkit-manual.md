# Classic parkit Manual Flow (Legacy)

This is the older manual multi-step path. Prefer `projark` unless you need step-level control.

## Sequence

```bash
parkit createtar --folder /data/CCBR/projects/ccbr_12345
parkit createemptycollection --dest /CCBR_Archive/GRIDFTP/Project_CCBR-12345 --projectdesc "testing" --projecttitle "test project"
parkit createmetadata --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/Project_CCBR-12345
parkit deposittar --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/Project_CCBR-12345
```

## Why Legacy

- More manual steps
- Higher operator overhead
- Easier to miss preflight/session safeguards that `projark` includes by default
