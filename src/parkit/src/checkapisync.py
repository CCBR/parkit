"""Check whether the local HPC_DME_APIs clone is at its expected git ref.

The expected ref is the latest stable ``releases/X.Y.Z`` branch (the
highest-numbered one merged into ``master``), unless a tag or branch is
pinned with ``--ref`` or the ``HPC_DME_APIs_REF`` environment variable.

Example:
    parkit checkapisync
    parkit checkapisync --ref releases/3.31.0
"""

from parkit.src.hpcdme_release import (
    HpcDmeRepoError,
    current_branch,
    current_release_version,
    format_version,
    head_sha,
    requested_ref,
    resolve_repo_path,
    resolve_sync_target,
    same_tree,
)


def check_hpc_dme_apis_sync(repo_override: str = "", ref: str = "") -> int:
    """Report whether HPC_DME_APIs is in sync with its expected ref.

    Args:
        repo_override: Optional path to the HPC_DME_APIs repository.
        ref: Optional tag or branch to compare against; defaults to
            ``HPC_DME_APIs_REF`` or, failing that, the latest stable release.

    Returns:
        0 when in sync, 1 when out of sync, 2 on configuration errors.
    """
    rc = 0
    try:
        repo = resolve_repo_path(repo_override=repo_override)
        print(f"HPC_DME_APIs={repo}")
        target = resolve_sync_target(repo, requested_ref(ref))
        local = head_sha(repo)
        local_version = current_release_version(repo)
        label = "pinned ref" if target.pinned else "latest stable release"

        print(f"branch={current_branch(repo)}")
        print(f"local={local}")
        print(f"local_release={format_version(local_version)}")
        print(f"target={target.name} ({label}, {target.kind})")
        print(f"target_sha={target.sha}")
        print(f"target_release={target.version_str}")

        if local == target.sha:
            print(f"IN SYNC: local repo is at {target.name}.")
        elif same_tree(repo, "HEAD", target.sha):
            print(f"IN SYNC: local history differs, but content matches {target.name}.")
        elif (
            not target.pinned
            and local_version is not None
            and target.version is not None
            and local_version > target.version
        ):
            print(
                f"IN SYNC: local release {format_version(local_version)} is newer "
                f"than the latest stable release {target.version_str}; "
                "not downgrading."
            )
        else:
            rc = 1
            if (
                local_version is not None
                and target.version is not None
                and local_version < target.version
            ):
                reason = (
                    f"local release {format_version(local_version)} is older than "
                    f"{target.name}."
                )
            else:
                reason = f"local repo is not at {target.name}."
            print(f"OUT OF SYNC: {reason} Run 'parkit syncapi' to update.")
    except HpcDmeRepoError as exc:
        rc = exc.exit_code
        print(f"checkapisync failed: {exc}")
        if exc.hint:
            print(f"checkapisync hint: {exc.hint}")
    return rc
