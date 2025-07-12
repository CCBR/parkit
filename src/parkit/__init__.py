import os
from parkit.src.utils import *

hpc = ""
if os.environ.get("HOSTNAME") == "helix.nih.gov":
    hpc = "helix"
elif which("scontrol") != None:
    cmd = "scontrol show config"

    proc = run_cmd(
        cmd=cmd,
        returnproc=True,
        errormsg="scontrol failed!",
        exitiffails=False,
        echocmd=False,
    )

    if "biowulf" in proc.stdout:
        hpc = "biowulf"
    elif "fsitgl" in proc.stdout:
        hpc = "frce"

if os.environ.get("HPC_DM_UTILS") is None:
    if os.environ.get("USER") == "kopardevn":
        if hpc == "biowulf" or hpc == "helix":
            os.environ["HPC_DM_UTILS"] = "/data/kopardevn/SandBox/HPC_DME_APIs/utils"
    else:
        errorout(
            msg="HPC_DM_UTILS in unset! ... try... export HPC_DM_UTILS=/path/to/HPC_DME_APIs/utils"
        )

if hpc == "biowulf" or hpc == "helix":
    os.environ[
        "SOURCE_CONDA_CMD"
    ] = '. "/data/CCBR_Pipeliner/db/PipeDB/Conda/etc/profile.d/conda.sh"'
else:
    errorout("SOURCE_CONDA_CMD environmental variable needs to be set explicitly!")

if os.environ.get("HPC_DM_JAVA_VERSION") is None:
    if hpc == "biowulf" or hpc == "helix":
        warning("HPC_DM_JAVA_VERSION is not set, setting it to 23.0.2")
        warning(
            "If you need a different version, please set it explicitly in your environment."
        )
        os.environ["HPC_DM_JAVA_VERSION"] = "23.0.2"
    else:
        errorout(
            msg="HPC_DM_JAVA_VERSION in unset! ... try... export HPC_DM_JAVA_VERSION=23.0.2"
        )
