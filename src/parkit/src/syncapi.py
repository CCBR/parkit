"""Move the local HPC_DME_APIs clone to its expected ref and refresh the token.

The expected ref is the latest stable ``releases/X.Y.Z`` branch (the
highest-numbered one merged into ``master``), unless a tag or branch is
pinned with ``--ref`` or the ``HPC_DME_APIs_REF`` environment variable.
The automatic target never downgrades; an explicitly pinned ref may.

Example:
    parkit syncapi
    parkit syncapi --ref 3.31.0
"""

import subprocess
from pathlib import Path

from parkit.src.hpcdme_release import (
    HpcDmeRepoError,
    SyncTarget,
    checkout_target,
    current_branch,
    current_release_version,
    format_version,
    has_tracked_changes,
    head_sha,
    jar_version_at,
    requested_ref,
    resolve_repo_path,
    resolve_sync_target,
)


def _locate_functions_file(repo: Path) -> Path:
    """Return the HPC_DME_APIs ``functions`` file used to generate tokens."""
    functions_file = repo / "functions"
    if not functions_file.exists():
        functions_file = repo / "utils" / "functions"
    if not functions_file.exists():
        raise HpcDmeRepoError(
            f"could not find functions file at {repo / 'functions'} "
            f"or {repo / 'utils' / 'functions'}."
        )
    return functions_file


def _generate_token(functions_file: Path) -> None:
    """Run ``dm_generate_token`` interactively.

    Raises:
        HpcDmeRepoError: if token generation fails.
    """
    # Must run in a shell because source is a shell builtin.
    token_cmd = f'source "{functions_file}" && dm_generate_token'
    if subprocess.run(["bash", "-lc", token_cmd], check=False).returncode != 0:
        raise HpcDmeRepoError(
            "dm_generate_token was not successful.",
            hint=(
                "verify credentials and LDAP access, then rerun this command. "
                "If needed, inspect HPC_DME_APIs/utils/temp/log for details."
            ),
        )


def _move_to_target(repo: Path, target: SyncTarget) -> None:
    """Check out ``target`` unless that would silently downgrade the clone."""
    local = head_sha(repo)
    local_version = current_release_version(repo)
    print(
        f"syncapi: local {current_branch(repo)} "
        f"(release {format_version(local_version)}) -> target {target.name} "
        f"(release {target.version_str})"
    )
    newer_locally = (
        local_version is not None
        and target.version is not None
        and local_version > target.version
    )

    if local == target.sha:
        print(f"syncapi: already at {target.name}; nothing to update.")
    elif newer_locally and not target.pinned:
        print(
            f"syncapi: local release {format_version(local_version)} is newer than "
            f"the latest stable release {target.version_str}; leaving it unchanged."
        )
    else:
        if newer_locally:
            print(
                f"syncapi: WARNING: downgrading from {format_version(local_version)} "
                f"to {target.version_str} as requested by --ref/HPC_DME_APIs_REF."
            )
        if has_tracked_changes(repo):
            raise HpcDmeRepoError(
                "the repository has uncommitted changes to tracked files.",
                hint="commit, stash, or discard them (see 'git status'), then retry.",
            )
        checkout_target(repo, target)
        if head_sha(repo) != target.sha:
            raise HpcDmeRepoError(
                f"after checkout, HEAD is not at {target.name} ({target.sha})."
            )
        print(f"syncapi: now at {target.name} ({target.sha[:10]}).")

        jar_version = jar_version_at(repo, "HEAD")
        if (
            jar_version is not None
            and target.version is not None
            and jar_version[:2] != target.version[:2]
        ):
            print(
                f"syncapi: WARNING: utils/version lists hpc-cli "
                f"{format_version(jar_version)}, which does not match release "
                f"{target.version_str}."
            )


def syncapi(repo_override: str = "", ref: str = "") -> int:
    """Sync HPC_DME_APIs to its expected ref, then generate a fresh token.

    Args:
        repo_override: Optional path to the HPC_DME_APIs repository.
        ref: Optional tag or branch to sync to; defaults to
            ``HPC_DME_APIs_REF`` or, failing that, the latest stable release.

    Returns:
        0 on success, 1 on sync/token failures, 2 on configuration errors.
    """
    rc = 0
    print("syncapi: starting HPC_DME_APIs sync and token refresh")
    try:
        repo = resolve_repo_path(repo_override=repo_override)
        print(f"HPC_DME_APIs={repo}")

        print("syncapi: [1/4] fetching release branches and resolving target ...")
        target = resolve_sync_target(repo, requested_ref(ref))
        label = "pinned ref" if target.pinned else "latest stable release"
        print(f"syncapi: target is {target.name} ({label}, {target.kind})")

        print("syncapi: [2/4] moving local repo to target ...")
        _move_to_target(repo, target)

        print("syncapi: [3/4] locating HPC_DME_APIs functions file ...")
        functions_file = _locate_functions_file(repo)

        print("syncapi: [4/4] generating a fresh token via dm_generate_token ...")
        print(
            "syncapi: interactive prompt expected; enter your host password when asked."
        )
        _generate_token(functions_file)
        print("Now you are in sync and ready to run other parkit commands.")
    except HpcDmeRepoError as exc:
        rc = exc.exit_code
        print(f"syncapi failed: {exc}")
        if exc.hint:
            print(f"syncapi hint: {exc.hint}")
    return rc
