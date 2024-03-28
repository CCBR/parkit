## parkit

**Park** an **arc**hived project tool**kit**!

> DISCLAIMERS:
>
> - works only on [BIOWULF](https://hpc.nih.gov/) or HELIX
> - moves files to [HPC-DME](https://hpcdmeweb.nci.nih.gov/login)

### Prerequisites:

- On helix or biowulf you can get access to `parkit` by loading the appropriate conda env

```bash
%> . "/data/CCBR_Pipeliner/db/PipeDB/Conda/etc/profile.d/conda.sh"
%> conda activate parkit
```

If not on helix or biowulf then you will have to **clone** the repo and **pip install** it.

- [HPC_DME_APIs](https://github.com/CBIIT/HPC_DME_APIs) package needs to be cloned and set up correctly. Run `dm_generate_token` to successfully generate a token prior to running `parkit`.

- **HPC_DM_UTILS** environmental variable should be preset before calling `parkit`. It also needs to be passed as an argument to `parkit_folder2hpcdme` and `parkit_tarball2hpcdme` end-to-end workflows.

### Usage:

```bash
%> parkit --help
usage: parkit [-h] {createtar,createmetadata,createemptycollection,deposittar} ...

parkit subcommands to park data in HPCDME

positional arguments:
  {createtar,createmetadata,createemptycollection,deposittar}
                        Subcommand to run
    createtar           create tarball(and its filelist) from a project folder.
    createmetadata      create the metadata.json file required for a tarball (and its filelist)
    createemptycollection
                        creates empty project and analysis collections
    deposittar          deposit tarball(and filelist) into vault

options:
  -h, --help            show this help message and exit
```

### Example:

- Say you want to archive `/data/CCBR/projects/CCBR-12345` folder to `/CCBR_Archive/GRIDFTP/CCBR-12345` collection on HPC-DME
- you can run the following commands sequentially to do this:

```bash
# create the tarball
%> parkit createtar --folder /data/CCBR/projects/ccbr_12345

# create an empty collection on HPC-DME
%> parkit createemptycollection --dest /CCBR_Archive/GRIDFTP/CCBR-12345 --projectdesc "testing" --projecttitle "test project 1"

# create required metadata
%> parkit createmetadata --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/CCBR-12345

# deposit the tar into HPC-DME
%> parkit deposittar --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/CCBR-12345

# bunch of extra files are created in the process
%> ls /data/CCBR/projects/ccbr_12345.tar*
/data/CCBR/projects/ccbr_12345.tar           /data/CCBR/projects/ccbr_12345.tar.filelist.md5            /data/CCBR/projects/ccbr_12345.tar.md5
/data/CCBR/projects/ccbr_12345.tar.filelist  /data/CCBR/projects/ccbr_12345.tar.filelist.metadata.json  /data/CCBR/projects/ccbr_12345.tar.metadata.json

# these extra files can now be deleted
%> rm -f /data/CCBR/projects/ccbr_12345.tar*

# you can also deleted the recently parked project folder
%> rm -rf /data/CCBR/projects/ccbr_12345

# test results with
%> dm_get_collection /CCBR_Archive/GRIDFTP/CCBR-12345
# Done!
```

We also have end-to-end slurm-supported folder-to-hpcdme and tarball-to-hpcdme workflows:

- `parkit_folder2hpcdme`
- `parkit_tarball2hpcdme`

```bash
%> parkit_folder2hpcdme --help
usage: parkit_folder2hpcdme [-h] [--restartfrom RESTARTFROM] [--executor EXECUTOR] [--folder FOLDER] [--dest DEST]
                            [--projectdesc PROJECTDESC] [--projecttitle PROJECTTITLE] [--cleanup] --hpcdmutilspath HPCDMUTILSPATH
                            [--version]

End-to-end parkit: Folder 2 HPCDME

options:
  -h, --help            show this help message and exit
  --restartfrom RESTARTFROM
                        if restarting then restart from this step. Options are: createemptycollection, createmetadata, deposittar
  --executor EXECUTOR   slurm or local
  --folder FOLDER       project folder to archive
  --dest DEST           vault collection path (Analysis goes under here!)
  --projectdesc PROJECTDESC
                        project description
  --projecttitle PROJECTTITLE
                        project title
  --cleanup             post transfer step to delete local files
  --hpcdmutilspath HPCDMUTILSPATH
                        what should be the value of env var HPC_DM_UTILS
  --version             print version
```

```bash
parkit_tarball2hpcdme --help
usage: parkit_tarball2hpcdme [-h] [--restartfrom RESTARTFROM] [--executor EXECUTOR] [--tarball TARBALL] [--dest DEST]
                             [--projectdesc PROJECTDESC] [--projecttitle PROJECTTITLE] [--cleanup] --hpcdmutilspath HPCDMUTILSPATH
                             [--version]

End-to-end parkit: Tarball 2 HPCDME

options:
  -h, --help            show this help message and exit
  --restartfrom RESTARTFROM
                        if restarting then restart from this step. Options are: createemptycollection, createmetadata, deposittar
  --executor EXECUTOR   slurm or local
  --tarball TARBALL     project tarball to archive
  --dest DEST           vault collection path (Analysis goes under here!)
  --projectdesc PROJECTDESC
                        project description
  --projecttitle PROJECTTITLE
                        project title
  --cleanup             post transfer step to delete local files
  --hpcdmutilspath HPCDMUTILSPATH
                        what should be the value of env var HPC_DM_UTILS
  --version             print version
```
