import os
import subprocess
from pathlib import Path


def _resolve_repo_path(repo_override=""):
    if repo_override:
        return Path(repo_override)

    env_repo = os.environ.get("HPC_DME_APIs")
    if env_repo:
        return Path(env_repo)

    dm_utils = os.environ.get("HPC_DM_UTILS", "")
    if dm_utils:
        dm_utils_path = Path(dm_utils)
        if dm_utils_path.name == "utils":
            return dm_utils_path.parent

    fallback = Path("/data/kopardevn/SandBox/HPC_DME_APIs")
    if fallback.exists():
        return fallback

    return None


def syncapi(repo_override=""):
    print("syncapi: starting HPC_DME_APIs sync and token refresh")
    repo = _resolve_repo_path(repo_override=repo_override)
    if repo is None:
        print("syncapi failed: HPC_DME_APIs is not set and no fallback repo path was found.")
        print(
            "syncapi hint: set HPC_DME_APIs to your repo path, "
            "or set HPC_DM_UTILS to <HPC_DME_APIs>/utils."
        )
        return 2

    print(f"HPC_DME_APIs={repo}")
    if not (repo / ".git").exists():
        print(f"syncapi failed: not a git repository: {repo}")
        return 2

    print("syncapi: [1/3] pulling latest commits from upstream ...")
    pull_proc = subprocess.run(["git", "-C", str(repo), "pull"])
    if pull_proc.returncode != 0:
        print("syncapi failed: git pull did not succeed.")
        print("syncapi hint: resolve git conflicts or fix remote/authentication issues, then retry.")
        return 1

    print("syncapi: [2/3] locating HPC_DME_APIs functions file ...")
    functions_file = repo / "functions"
    if not functions_file.exists():
        alt_functions = repo / "utils" / "functions"
        if alt_functions.exists():
            functions_file = alt_functions
        else:
            print(
                f"syncapi failed: could not find functions file at {repo / 'functions'} "
                f"or {repo / 'utils' / 'functions'}."
            )
            return 1

    print("syncapi: [3/3] generating a fresh token via dm_generate_token ...")
    print("syncapi: interactive prompt expected; enter your host password when asked.")
    # Must run in a shell because source is a shell builtin.
    token_cmd = f'source "{functions_file}" && dm_generate_token'
    token_proc = subprocess.run(["bash", "-lc", token_cmd])
    if token_proc.returncode != 0:
        print("syncapi failed: dm_generate_token was not successful.")
        print(
            "syncapi hint: verify credentials and LDAP access, then rerun this command. "
            "If needed, inspect HPC_DME_APIs/utils/temp/log for details."
        )
        return 1

    print("Now you are in sync and ready to run other parkit commands.")
    return 0
