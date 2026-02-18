#!/usr/bin/env bash

SCRIPTNAME="$BASH_SOURCE"
SCRIPTDIRNAME=$(readlink -f $(dirname "$SCRIPTNAME"))

# add "bin" to PATH
if [[ ":$PATH:" != *":${SCRIPTDIRNAME}:"* ]];then
	export PATH=${PATH}:${SCRIPTDIRNAME}
fi

# rely on redirect to be redirect to the python script
RESOURCEDIR=$(dirname "$SCRIPTDIRNAME")
TOOLDIR="$SCRIPTDIRNAME"
TOOLNAME="parkit"
# PARKIT="${TOOLDIR}/${TOOLNAME}"
PARKIT="parkit"

# Check if --version is provided as the first argument
if [[ "$1" == "--version" ]]; then
    echo "projark is using the following parkit version:"
    ${PARKIT} --version
    exit 0
fi

# Test if parkit is working
${PARKIT} > /dev/null 2>&1 || { echo "${PARKIT} not found or cannot be run!"; exit 1; }

ARGPARSE_DESCRIPTION="Wrapper for folder2hpcdme for quick CCBR project archiving!"
source ${RESOURCEDIR}/resources/argparse.bash || exit 1
argparse "$@" <<EOF || exit 1
parser.add_argument('--folder',required=True,help='Input folder path to archive')
parser.add_argument('--projectnumber',required=True,help='CCBR project number.. destination will be /CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>')
parser.add_argument('--executor',required=False,default='slurm', help='slurm or local')
parser.add_argument('--rawdata',required=False,action='store_true', help='If tarball is rawdata and needs to go under folder Rawdata')
parser.add_argument('--cleanup',required=False,action='store_true', help='post transfer step to delete local files')
EOF

# Destination path for archiving
TITLE="CCBR-${PROJECTNUMBER}"
DEST="/CCBR_Archive/GRIDFTP/Project_${TITLE}"

# Check if SOURCE_CONDA_CMD is set
if [ -z "${SOURCE_CONDA_CMD}" ];then
    echo "SOURCE_CONDA_CMD env variable must be set"
    exit 1
else
    echo "SOURCE_CONDA_CMD is set to: $SOURCE_CONDA_CMD"
fi

# Check if HPC_DM_UTILS is set
if [ -z "$HPC_DM_UTILS" ]; then
  echo "HPC_DM_UTILS environment variable is not set."
  exit 1  # Exit the script with an error code
else
  echo "HPC_DM_UTILS is set to: $HPC_DM_UTILS"
fi

# Call folder2hpcdme with necessary parameters
cmd="parkit_folder2hpcdme --folder \"$FOLDER\" --dest \"$DEST\" --projecttitle \"$TITLE\" --projectdesc \"$TITLE\" --executor \"$EXECUTOR\" --hpcdmutilspath $HPC_DM_UTILS --makereadme"
if [[ "${RAWDATA}" == "yes" ]];then
    cmd="${cmd} --rawdata"
fi
if [[ "${CLEANUP}" == "yes" ]];then
    cmd="${cmd} --cleanup"
fi
echo $cmd
eval "$cmd"
if [[ "$?" != "0" ]];then
    exit 1
fi

# Exit with the same status code as folder2hpcdme
exit $?
