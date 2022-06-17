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
import subprocess

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
    parser.add_argument('-o', dest='outfile', required=True,
        help='Outfile Path with one dataobject per line')
    parser.add_argument('-f', dest='filetype', required=False,
        help='Extension of files to output eg. FASTQ')
    parser.add_argument('-t', dest='tmpdir', required=False, default = '/dev/shm',
        help='temp folder location')


    args = parser.parse_args()
    return args

def _create_random_json_path(args):
    return args.tmpdir+os.sep+str(uuid.uuid4())+".json"

def _create_query_json(args,page=1):
    """
    Create the json required for query
    """
    # import json
    # import uuid
    # import os
    queryDict = dict()
    queryDict['page'] = page
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
    if args.filetype:
        query2 = dict()
        query2['attribute'] = 'file_type'
        query2['operator'] = 'EQUAL'
        ft = args.filetype
        query2['value'] = ft.upper()
        queryDict['compoundQuery']['queries'].append(query2)
    
    json_file_path = _create_random_json_path(args)
    out_file = open(json_file_path, "w")
    json.dump(queryDict, out_file, indent = 6)
    out_file.close()
    return json_file_path

def check_path():
    if not _cmd_exists('dm_query_dataobject'):
        exit('HPCDMEAPIs are not setup correctly! dm_query_dataobject is not in PATH.')

def _create_cmd(qjson,ojson,args):
    cmd = "dm_query_dataobject -o "
    cmd += ojson
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
    jsons2delete = []
    qjson = _create_query_json(args)
    jsons2delete.append(qjson)
    data_objects = []
    page1json = _create_random_json_path(args)
    jsons2delete.append(page1json)
    cmd = _create_cmd(qjson,page1json,args)
    print(cmd)
    subprocess.run(cmd,shell=True,capture_output=True)
    with open(page1json) as page1output:
        page1dict = json.load(page1output)
        data_objects.extend(page1dict['dataObjectPaths'])
    total_count = page1dict['totalCount']
    total_pages = total_count/100 + 1
    for page in range(2,total_pages+1):
        qjson = _create_query_json(args,page)
        ojson = _create_random_json_path(args)
        jsons2delete.append(qjson)
        jsons2delete.append(ojson)
        cmd = _create_cmd(qjson,ojson,args)
        print(cmd)
        subprocess.run(cmd,shell=True,capture_output=True)
        with open(ojson) as output:
            outdict = json.load(output)
            data_objects.extend(outdict['dataObjectPaths'])    
    _write_objects(data_objects)
    _cleanup(jsons2delete)

def _write_objects(data_objects,args):
    """
    write list of data objects to output file
    one object per line
    """
    with open(args.out_file, 'w') as fp:
        for obj in data_objects:
            fp.write("%s\n" % obj)

            
def _cleanup(files2delete):
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
    check_path()
    # Collect args 
    args = collect_args()
    # run the query
    run_query(args)


if __name__ == '__main__':
    main()