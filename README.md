## parkit 🅿️🚙

**Park** an **arc**hived project tool**kit**!

> DISCLAIMERS:
>
> - works only on [BIOWULF](https://hpc.nih.gov/) or HELIX
> - moves files to [HPC-DME](https://hpcdmeweb.nci.nih.gov/login)

### Usage:

```bash
./parkit --help
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
./parkit createtar --folder /data/CCBR/projects/ccbr_12345

# create an empty collection on HPC-DME
./parkit createemptycollection --dest /CCBR_Archive/GRIDFTP/CCBR-12345 --projectdesc "testing" --projecttitle "test project 1"

# create required metadata
./parkit createmetadata --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/CCBR-12345

# deposit the tar into HPC-DME
./parkit deposittar --tarball /data/CCBR/projects/ccbr_12345.tar --dest /CCBR_Archive/GRIDFTP/CCBR-12345

# bunch of extra files are created in the process
ls /data/CCBR/projects/ccbr_12345.tar*
/data/CCBR/projects/ccbr_12345.tar           /data/CCBR/projects/ccbr_12345.tar.filelist.md5            /data/CCBR/projects/ccbr_12345.tar.md5
/data/CCBR/projects/ccbr_12345.tar.filelist  /data/CCBR/projects/ccbr_12345.tar.filelist.metadata.json  /data/CCBR/projects/ccbr_12345.tar.metadata.json

# these extra files can now be deleted
rm -f /data/CCBR/projects/ccbr_12345.tar*

# you can also deleted the recently parked project folder
rm -rf /data/CCBR/projects/ccbr_12345

# Done!
```

`parkit_e2e` can be used to run all the above sequentially via "slurm".
