import os, sys
import uuid
import subprocess
import hashlib


def has_write_permission(folder_path):
    return os.access(folder_path, os.W_OK)


def is_folder(path):
    return os.path.isdir(path)


def check_file_exists(filepath):
    if os.path.exists(filepath):
        return True


def _cmd_exists(cmd, path=None):
    """test if path contains an executable file with name"""
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False


def check_path(executable):
    if not _cmd_exists(executable):
        exit("HPCDMEAPIs are not setup correctly! %s is not in PATH." % (executable))


def create_random_path(tmpdir, extension):
    """
    create random file name with the provided extension in the provided folder
    """
    if tmpdir.endswith(os.sep):
        return tmpdir + str(uuid.uuid4()) + extension
    else:
        return tmpdir + os.sep + str(uuid.uuid4()) + extension


def run_cmd(cmd, errormsg=""):
    """
    run the cmd with subprocess and check for errors
    """
    print(cmd)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    exitcode = str(proc.returncode)
    if exitcode != "0":
        print("returncode:" + exitcode)
        so = str(proc.stdout)
        # so_test = "Error Code: 503" in so
        print("stdout:" + so)
        # print("503:"+str(so_test))
        se = str(proc.stderr)
        print("stderr:" + se)
        # se_test = "Error Code: 503" in se
        # print("503:"+str(se_test))
        exit(errormsg)


def delete_listoffiles(files2delete):
    """
    Deletes all the files in the provided list.
    """
    # import os
    for file in files2delete:
        os.remove(file)


def errorout(msg):
    print(f"ERROR:{msg}")
    sys.exit(1)


def warning(msg):
    print(f"WARNING:{msg}")


def get_md5sum(file_path):
    with open(file_path, "rb") as file:
        file_hash = hashlib.md5()
        while chunk := file.read(8192):
            file_hash.update(chunk)
        return file_hash.hexdigest()


def run_dm_cmd(dm_cmd, errormsg=""):
    # env_vars = {
    #     'HPC_DM_UTILS': '/data/kopardevn/SandBox/HPC_DME_APIs/utils'
    # }
    cmd = f"export HPC_DM_UTILS=/data/kopardevn/SandBox/HPC_DME_APIs/utils && source $HPC_DM_UTILS/functions && {dm_cmd}"
    print(cmd)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        shell=True,
        text=True,
        # env=env_vars
    )
    exitcode = str(proc.returncode)
    if exitcode != "0":
        print("returncode:" + exitcode)
        so = str(proc.stdout)
        # so_test = "Error Code: 503" in so
        print("stdout:" + so)
        # print("503:"+str(so_test))
        se = str(proc.stderr)
        print("stderr:" + se)
        # se_test = "Error Code: 503" in se
        # print("503:"+str(se_test))
        exit(errormsg)
