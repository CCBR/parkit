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
   % rename_files -i /Vault/Path -o <output json> 
"""

__author__ = 'Vishal Koparde'
__email__ = 'vishal.koparde@nih.gov'

import argparse
import os
import json
import uuid
import subprocess

def main():
    # check if HPCDME set up correctly
    check_path()
    # Collect args 
    args = collect_args()
    # run the query
    run_query(args)


if __name__ == '__main__':
    main()