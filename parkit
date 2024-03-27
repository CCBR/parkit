#!/usr/bin/env python3

import argparse
from src.createtar import createtar, tarprep
from src.createmetadata import createmetadata
from src.createemptycollection import createemptycollection
from src.deposittar import deposittocollection
from src.VersionCheck import __version__


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

    # Parse the arguments
    args = parser.parse_args()
    files_created = list()

    subcommands = ["createtar", "createmetadata", "createemptycollection", "deposittar"]
    if not args.command in subcommands:
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
        tar_json_path = createmetadata(args.tarball, args.dest)
        files_created.append(tar_json_path)
        filelist_json_path = createmetadata(args.tarball + ".filelist", args.dest)
        files_created.append(filelist_json_path)
    elif args.command == "deposittar":
        deposittocollection(args.tarball, args.dest)
    for f in files_created:
        print(f"createmetadata: {f} file was created!")


if __name__ == "__main__":
    main()
