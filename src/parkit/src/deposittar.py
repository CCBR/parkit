from pathlib import Path
from parkit.src.utils import *
from uuid import uuid4
import json
import os

import json

def update_object_name(input_json_path, new_object_name, new_alias, output_json_path):
    """
    Reads a metadata.JSON file with a metadataEntries list, updates the object_name attribute,
    and writes the updated metadata.JSON to a new file.

    Parameters:
        input_json_path (str): Path to the input JSON file.
        new_object_name (str): New value to assign to the 'object_name' attribute.
        new_alias (str): New value to assign to the 'alias' attribute.
        output_json_path (str): Path to the output JSON file.
    """
    with open(input_json_path, 'r') as infile:
        data = json.load(infile)

    found = False
    for entry in data.get("metadataEntries", []):
        if entry.get("attribute") == "object_name":
            entry["value"] = new_object_name
            found = True
            break

    if not found:
        raise ValueError("object_name attribute not found in metadataEntries.")

    found = False
    base_name = os.path.basename(new_object_name)
    for entry in data.get("metadataEntries", []):
        if entry.get("attribute") == "sample_name":
            entry["value"] = base_name
            found = True
            break

    if not found:
        raise ValueError("sample_name attribute not found in metadataEntries.")

    found = False
    for entry in data.get("metadataEntries", []):
        if entry.get("attribute") == "alias":
            entry["value"] = new_alias
            found = True
            break

    if not found:
        raise ValueError("alias attribute not found in metadataEntries.")

    with open(output_json_path, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    print(f"Updated JSON written to {output_json_path}")
    return True


def write_json(objectPath, outJSON):
    """
    Writes a JSON file in the following format:
    {
        "compoundQuery": {
            "operator": "AND",
            "queries": [
                {
                    "attribute": "object_name",
                    "value": "<objectPath>",
                    "operator": "LIKE"
                }
            ]
        },
        "detailedResponse": false,
        "page": 1,
        "totalCount": true
    }

    Parameters:
        objectPath (str): Path to the data object on the objectstore.
        outJSON (str): Name of output JSON file (e.g. "output.json")
    """
    data = {
        "compoundQuery": {
            "operator": "AND",
            "queries": [
                {
                    "attribute": "object_name",
                    "value": objectPath,
                    "operator": "EQUAL"
                }
            ]
        },
        "detailedResponse": False,
        "page": 1,
        "totalCount": True
    }

    with open(outJSON, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"JSON file written to {outJSON}")
    return True



def check_if_object_exists(objectPath):
    """
    Check if a data object exists in the specified collection path.
    
    Parameters:
    - objectPath: Path to the data object on the objectstore.
    
    Returns:
    - True if the object exists, False otherwise.
    """
    jsonName = str(uuid4()) + ".json"
    write_json(objectPath, jsonName)
    cmd = f"dm_query_dataobject {jsonName}"
    proc = run_dm_cmd(
        dm_cmd=cmd,
        errormsg="check_if_object_exists: dm_query_dataobject Failed!",
        returnproc=True,
        exitiffails=False
    )
    os.remove(jsonName)
    if proc.returncode != 0:
        if "no content for the specified item" in proc.stderr:
            return False
        else:
            errorout(
                msg=f"check_if_object_exists: dm_query_dataobject Failed! {proc.stderr}"
            )
    else:
        return True


# List of known compound extensions to support
COMPOUND_EXTENSIONS = [
    ".tar.gz", ".tar.bz2", ".tar.xz", ".fastq.gz", ".fq.gz",
    ".bam.bai", ".vcf.gz", ".fa.gz", ".fasta.gz", ".gtf.gz"
]

def split_compound_extension(filename):
    """
    Splits filename into root and extension, preserving known compound extensions.
    """
    for ext in sorted(COMPOUND_EXTENSIONS, key=len, reverse=True):
        if filename.endswith(ext):
            return filename[:-len(ext)], ext
    # fallback to default single extension split
    return os.path.splitext(filename)

def get_available_object_path(original_path):
    """
    Returns the next available object path, appending _002, _003, etc.
    before compound or regular extension.
    """
    if not check_if_object_exists(original_path):
        print(f"Object {original_path} does not exist, using original path...")
        return original_path

    # If the object already exists, generate a new name
    print(f"Object {original_path} already exists, generating a new name...")
    # Split the original path into directory and base name
    dir_name = os.path.dirname(original_path)
    base_name = os.path.basename(original_path)

    root, ext = split_compound_extension(base_name)

    count = 2
    while True:
        new_name = f"{root}_{count:03d}{ext}"
        new_path = os.path.join(dir_name, new_name)
        if not check_if_object_exists(new_path):
            print(f"Object {new_path} does not exist, using this path...")
            return new_path
        count += 1


def deposittocollection(tar, collectionpath, collectiontype): # collectiontype="Rawdata" for rawdata or "Analysis" for analysis

    p = Path(tar)
    p = p.absolute() # p is tar
    tar = str(p)
    tarmetadata = tar + ".metadata.json"
    tarfilelist = tar + ".filelist"
    tarfilelistmetadata = tar + ".filelist.metadata.json"

    analysis_collectionpath = collectionpath + "/" + collectiontype
    expected_tar_collectionpath = analysis_collectionpath + "/" + p.name
    tar_collectionpath = get_available_object_path(analysis_collectionpath + "/" + p.name)
    tarfilelist_collectionpath = tar_collectionpath + ".filelist"
    print(f"tar_collectionpath: {tar_collectionpath}")
    print(f"tarfilelist_collectionpath: {tarfilelist_collectionpath}")

    if expected_tar_collectionpath != tar_collectionpath:
        tar_dirname = os.path.dirname(p)
        new_tar_basename = os.path.basename(tar_collectionpath)

        new_tar = str(os.path.join(tar_dirname, new_tar_basename))
        new_tar_filelist = str(os.path.join(tar_dirname, new_tar_basename + ".filelist"))

        # Rename the tar file to the new path
        os.replace(tar, new_tar)
        tar = new_tar
        # Rename the tar filelist to the new path
        os.replace(tarfilelist, new_tar_filelist)
        tarfilelist = new_tar_filelist

        # Update the tar metadata and filelist metadata paths
        updated_tarmetadata = str(os.path.join(tar_dirname, new_tar_basename + ".metadata.json"))
        updated_tarfilelistmetadata = str(os.path.join(tar_dirname, new_tar_basename + ".filelist.metadata.json"))
        # Update metadata.json files to reflect the new object name
        update_object_name(tarmetadata, tar_collectionpath, tar, updated_tarmetadata)
        update_object_name(tarfilelistmetadata, tarfilelist_collectionpath, tarfilelist, updated_tarfilelistmetadata)

        tarmetadata = updated_tarmetadata
        tarfilelistmetadata = updated_tarfilelistmetadata
        # print("Updated paths:")
        # print(f"tar: {tar}")
        # print(f"tarfilelist: {tarfilelist}")
        # print(f"tarmetadata: {tarmetadata}")
        # print(f"tarfilelistmetadata: {tarfilelistmetadata}")

    files_deposited = list()

    cmd = (
        f"dm_register_dataobject_multipart {tarmetadata} {tar_collectionpath} {tar}"
    )
    proc = run_dm_cmd(
        dm_cmd=cmd,
        errormsg="deposittocollection: dm_register_dataobject_multipart Failed!",
        returnproc=True
    )
    if proc.returncode == 0:
        files_deposited.append(tar_collectionpath)
        print(f"tar {tar_collectionpath} deposited successfully!")

    cmd = f"dm_register_dataobject_multipart {tarfilelistmetadata} {tarfilelist_collectionpath} {tarfilelist}"
    # cmd = f"dm_register_dataobject {tarfilelistmetadata} {tarfilelist_collectionpath} {tarfilelist}"
    proc = run_dm_cmd(
        dm_cmd=cmd, errormsg="deposittocollection: dm_register_dataobject Failed!", returnproc=True
    )
    if proc.returncode == 0:
        files_deposited.append(tarfilelist_collectionpath)
        print(f"tarfilelist {tarfilelist_collectionpath} deposited successfully!")

    return files_deposited
