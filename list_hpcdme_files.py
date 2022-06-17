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
    parser.add_argument('-t', dest='filetype', required=False,
        help='Extension of files to output eg. FASTQ')

    args = parser.parse_args()
    return args



def main():

    # Collect args 
    args = collect_args()


if __name__ == '__main__':
    main()