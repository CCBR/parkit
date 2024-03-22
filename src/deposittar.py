from pathlib import Path
from src.utils import *


def deposittocollection(tar, collectionpath):
    p = Path(tar)
    p = p.absolute()

    analysis_collectionpath = collectionpath + "/Analysis"
    tar_collectionpath = analysis_collectionpath + "/" + p.name
    tarfilelist_collectionpath = analysis_collectionpath + "/" + p.name + ".filelist"
    tarmetadata = str(p) + ".metadata.json"
    tarfilelist = str(p) + ".filelist"
    tarfilelistmetadata = str(p) + ".filelist.metadata.json"

    cmd = f"dm_register_dataobject {tarfilelistmetadata} {tarfilelist_collectionpath} {tarfilelist}"
    run_dm_cmd(
        dm_cmd=cmd, errormsg="deposittocollection: dm_register_dataobject Failed!"
    )

    cmd = (
        f"dm_register_dataobject_multipart {tarmetadata} {tar_collectionpath} {str(p)}"
    )
    run_dm_cmd(
        dm_cmd=cmd,
        errormsg="deposittocollection: dm_register_dataobject_multipart Failed!",
    )
