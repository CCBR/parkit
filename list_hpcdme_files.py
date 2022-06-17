#!/usr/bin/env python

"""
Get a complete list of objects in HPCDME at a specified location in a given vault.
The result can be filtered for a user-specified filetype.
Usage:
   $ list_hpcdme_files -p /Vault/Path [-t <filetype>]
"""

__author__ = 'Vishal Koparde'
__email__ = 'vishal.koparde@nih.gov'

import argparse
import os
import json
import uuid

def _cmd_exists(cmd, path=None):
    """ test if path contains an executable file with name
    """
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False

def collect_args():
    """
    Collect all the parsed arguments and return the parser
    """
    # import argparse

    parser = argparse.ArgumentParser(description='List.')
    parser.add_argument('-p', dest='archivepath', required=True,
        help='Archive Path')
    parser.add_argument('-f', dest='filetype', required=False,
        help='Extension of files to output eg. FASTQ')
    parser.add_argument('-t', dest='tmpdir', required=False, default = '/dev/shm',
        help='temp folder location')


    args = parser.parse_args()
    return args

def create_json(args):
    """
    Create the json required for query
    """
    # import json
    # import uuid
    # import os
    queryDict = dict()
    queryDict['page'] = 1
    queryDict['totalCount'] = True
    queryDict['detailedResponse'] = False
    queryDict['compoundQuery'] = dict()
    queryDict['compoundQuery']['operator'] = 'AND'
    queryDict['compoundQuery']['queries'] = list()
    query1 = dict()
    query1['attribute'] = 'archive_file_id'
    query1['operator'] = 'LIKE'
    query1['value'] = '%'
    queryDict['compoundQuery']['queries'].append(query1)
    if not args.filetype:
        query2['attribute'] = 'file_type'
        query2['operator'] = 'EQUAL'
        query2['value'] = 'FASTQ'
        queryDict['compoundQuery']['queries'].append(query2)
    
    json_file_path = args.tmpdir+os.sep+str(uuid.uuid4())+".json"
    out_file = open(json_file_path, "w")
    json.dump(queryDict, out_file, indent = 6)
    out_file.close()
    return json_file_path
            
def cleanup(files2delete):
    """
    Deletes all the files in the provided list.
    """
    # import os
    for file in files2delete:
        os.remove(file)


def main():

    # files to delete ... make a list
    delfiles = []
    # check if HPCDME set up correctly
    if not _cmd_exists('dm_query_dataobject'):
        exit('HPCDMEAPIs are not setup correctly! dm_query_dataobject is not in PATH.')
    # Collect args 
    args = collect_args()
    # Create the query json
    qjson = create_json(args)
    delfiles.append(qjson)
    print(qjson)
    # delete temp files
    # cleanup(delfiles)


if __name__ == '__main__':
    main()