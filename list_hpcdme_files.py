#!/usr/bin/env python

"""
Get a complete list of objects in HPCDME at a specified location in a given vault.
The result can be filtered for a user-specified filetype.
Usage:
   $ list_hpcdme_files -p /Vault/Path [-t <filetype>]
"""

__author__ = 'Vishal Koparde'
__email__ = 'vishal.koparde@nih.gov'


def collect_args():
    """
    Collect all the parsed arguments and return the parser
    """
    import argparse

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
    import json
    import uuid
    import os
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
            


def main():

    # Collect args 
    args = collect_args()
    json = create_json(args)
    print(json)


if __name__ == '__main__':
    main()