#!/usr/bin/env python

"""
Get a complete list of objects in HPCDME at a specified collection in a given vault.
The result can be filtered for a user-specified filetype.
Usage:
   % list_hpcdme_files [-h] -p ARCHIVEPATH -o OUTFILE [-f FILETYPE] [-t TMPDIR]
Example:
    Save all fastq file paths in /CCBR_Archive vaults' GRIDFTP collection to a file named all_fastqs.txt
    % list_hpcdme_files -p /CCBR_Archive/GRIDFTP -o all_fastqs.txt -f fastq
"""

__author__ = "Vishal Koparde"
__email__ = "vishal.koparde@nih.gov"

import argparse
import json

from src.utils import *

PAGESIZE = 10000


def collect_args():
    """
    Collect all the parsed arguments and return the parser
    """
    # import argparse

    parser = argparse.ArgumentParser(
        description="list of objects in HPCDME collection."
    )
    parser.add_argument("-p", dest="archivepath", required=True, help="Archive Path")
    parser.add_argument(
        "-o",
        dest="outfile",
        required=True,
        help="Outfile Path with one dataobject per line",
    )
    parser.add_argument(
        "-f",
        dest="filetype",
        required=False,
        help="Extension of files to output eg. FASTQ",
    )
    parser.add_argument(
        "-t",
        dest="tmpdir",
        required=False,
        default="/dev/shm",
        help="temp folder location",
    )

    args = parser.parse_args()
    return args


def _create_query_json(args, page=1):
    """
    Create the json required for query
    """
    # import json
    # import uuid
    # import os
    queryDict = dict()
    queryDict["page"] = page
    queryDict["pageSize"] = PAGESIZE
    queryDict["totalCount"] = True
    queryDict["detailedResponse"] = False
    queryDict["compoundQuery"] = dict()
    queryDict["compoundQuery"]["operator"] = "AND"
    queryDict["compoundQuery"]["queries"] = list()
    query1 = dict()
    query1["attribute"] = "archive_file_id"
    query1["operator"] = "LIKE"
    query1["value"] = "%"
    queryDict["compoundQuery"]["queries"].append(query1)
    if args.filetype:
        query2 = dict()
        query2["attribute"] = "file_type"
        query2["operator"] = "EQUAL"
        ft = args.filetype
        query2["value"] = ft.upper()
        queryDict["compoundQuery"]["queries"].append(query2)

    json_file_path = create_random_path(args.tmpdir, ".json")
    outfile = open(json_file_path, "w")
    json.dump(queryDict, outfile, indent=6)
    outfile.close()
    return json_file_path


def _create_cmd(qjson, ojson, rest_response, args):
    cmd = "dm_query_dataobject"
    cmd += " -D " + rest_response
    cmd += " -o " + ojson
    cmd += " "
    cmd += qjson
    cmd += " "
    cmd += args.archivepath
    return cmd


def run_query(args):
    """
    a. run query page by page
    b. collect all output data objects into a list
    c. write data objects (one per line) to output file
    d. cleanup
    """
    files2delete = []
    qjson = _create_query_json(args)
    data_objects = []
    page1json = create_random_path(args.tmpdir, ".json")
    rest_response = create_random_path(args.tmpdir, ".txt")
    files2delete.append(qjson)
    files2delete.append(page1json)
    files2delete.append(rest_response)
    cmd = _create_cmd(qjson, page1json, rest_response, args)
    # print(cmd)
    # subprocess.run(cmd,shell=True,capture_output=True)
    errormsg = "HPCDMEAPI CLU dm_query_dataobject failed! See REST-response [file following the -D option] for more details."
    run_cmd(cmd, errormsg)
    with open(page1json) as page1output:
        page1dict = json.load(page1output)
        data_objects.extend(page1dict["dataObjectPaths"])
    total_count = page1dict["totalCount"]
    if total_count > PAGESIZE:
        total_pages = int(total_count / PAGESIZE) + 1
        for page in range(2, total_pages + 1):
            qjson = _create_query_json(args, page)
            ojson = create_random_path(args.tmpdir, ".json")
            files2delete.append(qjson)
            files2delete.append(ojson)
            files2delete.append(rest_response)
            cmd = _create_cmd(qjson, ojson, args)
            # print(cmd)
            # subprocess.run(cmd,shell=True,capture_output=True)
            run_cmd(cmd, errormsg)
            with open(ojson) as output:
                outdict = json.load(output)
                data_objects.extend(outdict["dataObjectPaths"])
    _write_objects(data_objects, args)
    delete_listoffiles(files2delete)


def _write_objects(data_objects, args):
    """
    write list of data objects to output file
    one object per line
    """
    with open(args.outfile, "w") as fp:
        for obj in data_objects:
            fp.write("%s\n" % obj)


def main():
    # check if HPCDME set up correctly
    check_path("dm_query_dataobject")
    # Collect args
    args = collect_args()
    # run the query
    run_query(args)


if __name__ == "__main__":
    main()
