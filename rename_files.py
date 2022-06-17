#!/usr/bin/env python

"""
Rename objects on HPCDME.
@Input
@param: TSV file
    TSV with 2 columns:
        column1 --> Old Archive Path
        column2 --> New Archive Path
@Output
@param: JSON file
    Rename json file that was parsed to dm_rename
Usage:
   % rename_files -i /Vault/Path [-o <output json>]
"""

__author__ = 'Vishal Koparde'
__email__ = 'vishal.koparde@nih.gov'

import argparse
import os
import json
import uuid
import subprocess

from src.utils import *

def collect_args():
    """
    Collect all the parsed arguments and return the parser
    """
    # import argparse

    parser = argparse.ArgumentParser(description='Rename objects on HPCDME.')
    parser.add_argument('-i', dest='inputtsv', required=True,
        help='2 column TSV with old and new archive paths.')
    parser.add_argument('-o', dest='outputjson', required=False,
        help='JSON file used to run dm_rename')
    parser.add_argument('-t', dest='tmpdir', required=False, default = '/dev/shm',
        help='temp folder location')
    args = parser.parse_args()
    return args

def _create_query_json(tsv,ojson):
    """
    Create the json required for query
    """
    queryDict = dict()
    queryDict['moveRequests'] = list()
    t = list(map(lambda x:x.strip().split("\t"),open(tsv,'r').readlines()))
    for l in t:
        entry = dict()
        entry['sourcePath'] = l[0]
        entry['destinationPath'] = l[1]
        queryDict['moveRequests'].append(entry)
    outfile = open(ojson, "w")
    json.dump(queryDict, outfile, indent = 6)
    outfile.close()
    return True

def _create_cmd(ojson,rest_response):
    cmd = "dm_rename"
    cmd += " -D " + rest_response
    cmd += " " + ojson
    return cmd

def rename(args):
    tsv = args.inputtsv

    #check if tsv exists
    if not check_file_exists(tsv):
        exit("%s file not found!"%(tsv))

    # check if file has 2 columns
    cmd = "awk -F\"\\t\" \'NF!=2 {exit 1}\' "+tsv
    errormsg = "%s file does not always have 2 columns!"%(tsv)
    run_cmd(cmd,errormsg)

    files2delete=[]

    # determine output json path
    if not args.outputjson:
        ojson = create_random_path(args.tmpdir,".json")
        files2delete.append(ojson)
    else:
        ojson = args.outputjson

    # create output json
    if not _create_query_json(tsv,ojson):
        exit("Creation of query json failed!")
    
    rest_response = create_random_path(args.tmpdir,".txt")
    files2delete.append(rest_response)
    cmd = _create_cmd(ojson,rest_response)
    errormsg = 'HPCDMEAPI CLU dm_rename failed! See REST-response [file following the -D option] for more details.'
    run_cmd(cmd,errormsg)
    delete_listoffiles(files2delete)


def main():
    # check if HPCDME set up correctly
    check_path('dm_rename')
    # Collect args 
    args = collect_args()
    # run the query
    rename(args)


if __name__ == '__main__':
    main()