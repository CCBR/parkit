import os
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

def check_path(executable):
    if not _cmd_exists(executable):
        exit('HPCDMEAPIs are not setup correctly! %s is not in PATH.'%(executable))

def _create_random_path(tmpdir,extension):
    """
    create random file name with the provided extension in the provided folder
    """ 
    if tmpdir.endswith(os.sep):
        return tmpdir+str(uuid.uuid4())+extension
    else:
        return tmpdir+os.sep+str(uuid.uuid4())+extension

def _run_cmd(cmd,errormsg):
    """
    run the cmd with subprocess and check for errors
    """
    print(cmd)
    proc = subprocess.run(cmd,shell=True,capture_output=True,text=True)
    exitcode = str(proc.returncode)
    if exitcode != '0':
        print("returncode:"+exitcode)
        so = str(proc.stdout)
        # so_test = "Error Code: 503" in so
        print("stdout:"+so)
        # print("503:"+str(so_test))
        se = str(proc.stderr)
        print("stderr:"+se)
        # se_test = "Error Code: 503" in se    
        # print("503:"+str(se_test))
        exit(errormsg)