# Verify Vault Contents

Use `projark ls` and `parkit ls` to confirm what has been archived in HPC-DME without needing to log in to the HPC-DME web portal.

## After a deposit — verify your project

Run immediately after `projark deposit` finishes (or up to 60 minutes later if files do not appear yet):

```bash
projark ls 982
```

Sizes default to exact bytes. Add `--human-readable` for decimal KB, MB, GB.

Expected output:

```
Project_CCBR-982  (1037000000000 B)
├── Analysis/  (571000000000 B)
│   ├── ccbr982.tar_0001                              500000000000 B     Vishal Koparde,260625
│   └── ccbr982.tar_0002                              71000000000 B      Vishal Koparde,260625
└── Rawdata/  (466000000000 B)
    └── ccbr982.tar                                   466000000000 B     Vishal Koparde,240429
```

!!! note "Index lag"
    HPC-DME's search index may lag up to **60 minutes** behind a recent deposit. If `projark ls` shows no results immediately after a deposit, wait and retry.

## View all archived projects

```bash
parkit ls /CCBR_Archive/GRIDFTP
```

This shows the entire archive organized by project, with per-project and per-subcollection size totals.

## Get file names before a selective retrieve

Use `--json` to extract filenames programmatically before running `projark retrieve --filenames`:

```bash
projark ls 982 --json | python3 -c "
import json, sys
for obj in json.load(sys.stdin):
    print(obj['path'].split('/')[-1])
"
```

Output:

```
ccbr982.tar_0001
ccbr982.tar_0002
ccbr982.tar_0001.md5
ccbr982.tar_0002.md5
ccbr982.tar.filelist
ccbr982.tar.md5
```

Then pass selected filenames to retrieve:

```bash
projark retrieve -p 982 -d Analysis \
  --filenames ccbr982.tar_0001,ccbr982.tar_0002 \
  --unsplit
```

## No special environment required

`projark ls` and `parkit ls` can be run from any terminal — no Helix host check, no tmux/screen, no API sync gate.
