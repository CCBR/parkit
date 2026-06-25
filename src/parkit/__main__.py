#!/usr/bin/env python3

import argparse
import sys
from parkit.src.createtar import createtar, tarprep
from parkit.src.createmetadata import createmetadata
from parkit.src.createemptycollection import createemptycollection
from parkit.src.deposittar import deposittocollection
from parkit.src.checkapisync import check_hpc_dme_apis_sync
from parkit.src.syncapi import syncapi
from parkit.src.lscollection import ls_collection
from parkit.src.utils import collection_exists
from parkit.src.VersionCheck import __version__


def main():
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="parkit subcommands to park data in HPCDME"
    )
    parser.add_argument("-v", "--version", action="version", version=__version__)
    # Create a subparser object
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Create a subcommand for "createtar"
    parser_createtar = subparsers.add_parser(
        "createtar", help="create tarball(and its filelist) from a project folder."
    )
    parser_createtar.add_argument(
        "--folder", type=str, help="path to project folder", required=True
    )
    parser_createtar.add_argument(
        "--outfile", type=str, help="path to output tarball", required=False, default=""
    )

    # Create a subcommand for "tarprep"
    parser_tarprep = subparsers.add_parser(
        "tarprep", help="prepare tarball for upload."
    )
    parser_tarprep.add_argument(
        "--tarball", type=str, help="path to tar file", required=True
    )

    # Create a subcommand for "checkapisync"
    parser_checkapisync = subparsers.add_parser(
        "checkapisync",
        help="check whether the HPC_DME_APIs repository is in sync with upstream",
    )
    parser_checkapisync.add_argument(
        "--repo",
        type=str,
        help="optional path to HPC_DME_APIs repository (overrides env/fallback)",
        required=False,
        default="",
    )

    # Create a subcommand for "syncapi"
    parser_syncapi = subparsers.add_parser(
        "syncapi",
        help="sync HPC_DME_APIs with upstream and generate a fresh token",
    )
    parser_syncapi.add_argument(
        "--repo",
        type=str,
        help="optional path to HPC_DME_APIs repository (overrides env/fallback)",
        required=False,
        default="",
    )

    # Create a subcommand for "createmetadata"
    parser_createmetadata = subparsers.add_parser(
        "createmetadata",
        help="create the metadata.json file required for a tarball (and its filelist)",
    )
    parser_createmetadata.add_argument("--tarball", type=str, help="path to tarball")
    parser_createmetadata.add_argument(
        "--dest",
        type=str,
        help="destination path in vault (Analysis collection goes under here)",
        required=True,
    )
    parser_createmetadata.add_argument(
        "--collectiontype",
        type=str,
        help="type of collection ... Analysis[default] or Rawdata",
        default="Analysis",  # or Rawdata
    )

    # Create a subcommand for "createemptycollection"
    parser_createemptycollection = subparsers.add_parser(
        "createemptycollection", help="creates empty project and analysis collections"
    )
    parser_createemptycollection.add_argument(
        "--dest",
        type=str,
        help="destination path in vault (Analysis collection goes under here)",
        required=True,
    )
    parser_createemptycollection.add_argument(
        "--projectdesc", type=str, help="project description", required=True
    )
    parser_createemptycollection.add_argument(
        "--projecttitle", type=str, help="project title", required=True
    )

    # Create a subcommand for "deposittar"
    parser_deposittar = subparsers.add_parser(
        "deposittar", help="deposit tarball(and filelist) into vault"
    )
    parser_deposittar.add_argument(
        "--tarball", type=str, help="path to tarball", required=True
    )
    parser_deposittar.add_argument(
        "--dest",
        type=str,
        help="destination path in vault (Analysis collection goes under here)",
        required=True,
    )
    parser_deposittar.add_argument(
        "--collectiontype",
        type=str,
        help="type of collection ... Analysis[default] or Rawdata",
        default="Analysis",  # or Rawdata
    )

    # Create a subcommand for "ls"
    parser_ls = subparsers.add_parser(
        "ls",
        help="list data objects under any HPC-DME collection path",
    )
    parser_ls.add_argument(
        "collection_path",
        metavar="COLLECTION_PATH",
        type=str,
        help="Full HPC-DME collection path (e.g. /CCBR_Archive/GRIDFTP/Project_CCBR-982)",
    )
    parser_ls.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit results as a JSON array instead of the tree view",
    )

    # Support "parkit <subcommand> --version" for all subcommands.
    subcommand_parsers = [
        parser_createtar,
        parser_tarprep,
        parser_checkapisync,
        parser_syncapi,
        parser_createmetadata,
        parser_createemptycollection,
        parser_deposittar,
        parser_ls,
    ]
    for subparser in subcommand_parsers:
        subparser.add_argument("-v", "--version", action="version", version=__version__)

    # Parse the arguments
    args = parser.parse_args()
    files_created = list()

    subcommands = [
        "createtar",
        "tarprep",
        "createmetadata",
        "createemptycollection",
        "deposittar",
        "checkapisync",
        "syncapi",
        "ls",
    ]
    if args.command not in subcommands:
        parser.print_help()
    elif args.command == "createtar":
        files_created = createtar(args.folder, args.outfile)
    elif args.command == "tarprep":
        files_created = tarprep(args.tarball)
    elif args.command == "createemptycollection":
        createemptycollection(
            args.dest, projectdesc=args.projectdesc, projecttitle=args.projecttitle
        )
    elif args.command == "createmetadata":
        tar_json_path = createmetadata(args.tarball, args.dest, args.collectiontype)
        files_created.append(tar_json_path)
        filelist_json_path = createmetadata(
            args.tarball + ".filelist", args.dest, args.collectiontype
        )
        files_created.append(filelist_json_path)
    elif args.command == "deposittar":
        files_deposited = deposittocollection(
            args.tarball, args.dest, args.collectiontype
        )
    elif args.command == "checkapisync":
        check_hpc_dme_apis_sync(args.repo)
    elif args.command == "syncapi":
        syncapi(args.repo)
    elif args.command == "ls":
        print(
            "Note: DME search index may lag up to 60 minutes behind recent deposits."
        )
        if not collection_exists(args.collection_path):
            print(f"ERROR: Collection does not exist in HPC-DME: {args.collection_path}")
            sys.exit(1)
        sys.exit(ls_collection(args.collection_path, json_output=args.json))
    for f in files_created:
        print(f"createmetadata: {f} file was created!")


if __name__ == "__main__":
    main()
