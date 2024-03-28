from parkit_pkg.src.utils import *
from pathlib import Path


def createtar(folder, outfile):
    created_files = []

    # check if path exists
    if not check_file_exists(folder):
        errorout(msg=f"{folder} does NOT exist!")

    # check if it is a folder
    if not is_folder(folder):
        errorout(msg=f"{folder} is NOT a folder!")

    # delete outfile if it exists
    if outfile != "" and check_file_exists(outfile):
        warning(f"{outfile} already exists! Deleting it and will recreate it.")
        os.remove(outfile)

    if outfile != "":
        p = Path(outfile)
        parent = p.parent
    else:
        p = Path(folder)
        parent = p.parent
        outfile = os.path.join(parent, p.name + ".tar")

    # check for write permissions:
    if not has_write_permission(parent):
        errorout(f"{parent} folder does NOT have write permissions!")

    # example
    # tar cvf ccbr913.tar ccbr913 ccbr913P2 > ccbr913.tar.filelist
    cmd = f"tar cvf {outfile} {folder} > {outfile}.filelist"
    run_cmd(cmd=cmd, errormsg="tar FAILED!")

    # calculate md5sum and write out to ".md5" files
    for f in [f"{outfile}.filelist", outfile]:
        md5sum = get_md5sum(f)
        md5sumfile = f + ".md5"
        with open(md5sumfile, "w") as of:
            of.write(f"{md5sum}\n")

    created_files.append(outfile)
    created_files.append(f"{outfile}.filelist")
    created_files.append(f"{outfile}.md5")
    created_files.append(f"{outfile}.filelist.md5")
    return created_files


def tarprep(tarfile):
    created_files = list()
    p = Path(tarfile)
    if p.suffix == ".gz":
        cmd = f"tar tzvf {tarfile} > {tarfile}.filelist"
    elif p.suffix == ".tar":
        cmd = f"tar tvf {tarfile} > {tarfile}.filelist"
    else:
        errorout('tarfile extension should be ".gz" or ".tar"')
    run_cmd(cmd=cmd, errormsg="getting filelist from tar file failed!")

    # calculate md5sum and write out to ".md5" files
    for f in [f"{tarfile}.filelist", tarfile]:
        md5sum = get_md5sum(f)
        md5sumfile = f + ".md5"
        with open(md5sumfile, "w") as of:
            of.write(f"{md5sum}\n")

    created_files.append(f"{tarfile}.filelist")
    created_files.append(f"{tarfile}.md5")
    created_files.append(f"{tarfile}.filelist.md5")
    return created_files
