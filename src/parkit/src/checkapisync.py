import os
import subprocess
from pathlib import Path


def _run_git(repo, args):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


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


def check_hpc_dme_apis_sync(repo_override=""):
    repo = _resolve_repo_path(repo_override=repo_override)
    if repo is None:
        print("HPC_DME_APIs is not set and no fallback repo path was found.")
        return 2

    print(f"HPC_DME_APIs={repo}")
    if not (repo / ".git").exists():
        print(f"Not a git repository: {repo}")
        return 2

    _run_git(repo, ["fetch", "--all", "--prune"])
    _, branch, _ = _run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    rc_local, local, err_local = _run_git(repo, ["rev-parse", "@"])
    rc_remote, remote, _ = _run_git(repo, ["rev-parse", "@{u}"])
    rc_base, base, _ = _run_git(repo, ["merge-base", "@", "@{u}"])
    rc_local_tree, local_tree, _ = _run_git(repo, ["rev-parse", "@^{tree}"])
    rc_remote_tree, remote_tree, _ = _run_git(repo, ["rev-parse", "@{u}^{tree}"])

    if rc_local != 0:
        print(f"Could not resolve local HEAD commit: {err_local}")
        return 2

    print(f"branch={branch}")
    print(f"local={local}")
    if rc_remote != 0:
        print("No upstream tracking branch configured.")
        return 2

    print(f"remote={remote}")
    print(f"base={base}")

    if local == remote:
        print("IN SYNC: local repo matches upstream.")
        return 0

    # Ignore local merge-only history drift when repository content is identical.
    # This commonly happens when local pulls create merge commits like:
    # "Merge branch 'master' of https://github.com/CBIIT/HPC_DME_APIs".
    if rc_local_tree == 0 and rc_remote_tree == 0 and local_tree == remote_tree:
        print("IN SYNC: local history differs, but repository content matches upstream.")
        return 0

    if rc_base != 0:
        print("OUT OF SYNC: local and remote differ.")
        return 1

    if local == base:
        print("OUT OF SYNC: local repo is behind upstream.")
        return 1

    if remote == base:
        print("OUT OF SYNC: local repo is ahead of upstream.")
        return 1

    print("OUT OF SYNC: local and upstream have diverged.")
    return 1
