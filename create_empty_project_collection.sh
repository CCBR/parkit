#!/usr/bin/env bash

path_to_executable=$(which dm_register_collection)
if [ ! -x "$path_to_executable" ] ; then
HPCDME toolkit setup
export HPC_DM_UTILS=/data/kopardevn/SandBox/HPC_DME_APIs/utils
source $HPC_DM_UTILS/functions
fi

dt=$(date '+%Y%m%d')
script_path=$(readlink -f $0)
parkit_dir=$(dirname $script_path)
uuid=$(echo $RANDOM | md5sum | head -c 20; echo;)
tmp_dir="/dev/shm/$uuid"
echo $tmp_dir
mkdir -p $tmp_dir

if [ "$#" != "3" ];then
	echo "USAGE:"
	echo "Three arguments are required!!"
	echo "bash $0 <archive-path> <project_title> <project_description>"
	exit
fi

template="${parkit_dir}/empty_project_collection_json_template"

collection_path=$1
collection_base=$(echo $collection_path|awk -F"/" '{print $NF}')
metadata_path="/dev/shm/${collection_base}.metadata.json"
pt=$2
pd=$3

sed "s/DATE/${dt}/g" $template |
sed "s/PROJECTTITLE/${pt}/g" |
sed "s/PROJECTDESCRIPTION/${pd}/g" > $metadata_path

cat $metadata_path
# dm_register_collection [optional parameters] <description.json> <destination-path>

dme_cmd="dm_register_collection $metadata_path $collection_path"
echo $dme_cmd
$dme_cmd

# cleanup
rm -rf $tmp_dir
