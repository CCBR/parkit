"""Locate the local HPC_DME_APIs clone and the git ref it should be synced to.

CBIIT/HPC_DME_APIs no longer publishes GitHub tags or releases. Each release
lives on a ``releases/X.Y.Z`` branch, and a release is considered shipped
(stable) once that branch has been merged into ``master``. Newer
``releases/*`` branches that are not merged yet are still in development.

By default the sync target is the latest stable release. Users can pin a
specific tag or branch with ``--ref`` or the ``HPC_DME_APIs_REF`` environment
variable; ``X.Y.Z`` is shorthand for ``releases/X.Y.Z``.

Example:
    >>> repo = resolve_repo_path()
    >>> resolve_sync_target(repo).name
    'releases/3.30.1'
    >>> resolve_sync_target(repo, "3.31.0").name
    'releases/3.31.0'
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REMOTE = "origin"
MAINLINE_BRANCH = "master"
RELEASE_PREFIX = "releases/"
REF_ENV_VAR = "HPC_DME_APIs_REF"

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_RELEASE_BRANCH_RE = re.compile(r"^releases/(\d+)\.(\d+)\.(\d+)$")
_JAR_VERSION_RE = re.compile(r"hpc-cli-(\d+)\.(\d+)\.(\d+)\.jar")

Version = tuple[int, int, int]


class HpcDmeRepoError(Exception):
    """Raised when the HPC_DME_APIs repository cannot be inspected or synced.

    Attributes:
        hint: Optional suggestion telling the user how to recover.
        exit_code: Exit code the calling CLI command should return.
    """

    def __init__(self, message: str, hint: str = "", exit_code: int = 1):
        super().__init__(message)
        self.hint = hint
        self.exit_code = exit_code


@dataclass(frozen=True)
class SyncTarget:
    """A git ref on the remote that the local clone should be synced to.

    Attributes:
        name: Branch or tag name, e.g. ``releases/3.30.1`` or ``v3.20.0``.
        kind: ``"branch"`` or ``"tag"``.
        sha: Commit the ref points to.
        version: Release version, from the ref name or ``utils/version``.
        pinned: Whether the user requested this ref explicitly.
    """

    name: str
    kind: str
    sha: str
    version: Version | None
    pinned: bool

    @property
    def version_str(self) -> str:
        """Return the release version as ``X.Y.Z`` (or ``unknown``)."""
        return format_version(self.version)


def format_version(version: Version | None) -> str:
    """Return ``version`` as ``X.Y.Z``, or ``unknown`` when it is ``None``."""
    text = "unknown"
    if version is not None:
        text = ".".join(str(part) for part in version)
    return text


def parse_release_version(branch_name: str) -> Version | None:
    """Return the version encoded in a ``releases/X.Y.Z`` branch name.

    Names that do not match exactly (for example ``releases/1.5.2-candidate``,
    ``releases/CICD-pipeline-test`` or the misspelled ``releeases/3.3.0``)
    return ``None``.
    """
    match = _RELEASE_BRANCH_RE.match(branch_name)
    version = None
    if match:
        version = tuple(int(part) for part in match.groups())
    return version


def normalize_ref(ref: str) -> str:
    """Expand the ``X.Y.Z`` shorthand to ``releases/X.Y.Z``; keep other refs."""
    ref = ref.strip()
    if _VERSION_RE.match(ref):
        ref = f"{RELEASE_PREFIX}{ref}"
    return ref


def requested_ref(ref_override: str = "") -> str:
    """Return the user-requested ref from ``--ref`` or ``HPC_DME_APIs_REF``."""
    return (ref_override or os.environ.get(REF_ENV_VAR, "")).strip()


def run_git(
    repo: Path, args: list[str], check: bool = False
) -> subprocess.CompletedProcess:
    """Run ``git -C repo <args>`` and capture its output.

    Raises:
        HpcDmeRepoError: if ``check`` is true and git exits non-zero.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], check=False, capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise HpcDmeRepoError(f"'git {' '.join(args)}' failed: {detail}")
    return proc


def resolve_repo_path(repo_override: str = "") -> Path:
    """Return the local HPC_DME_APIs git repository to operate on.

    Resolution order: ``repo_override``, the ``HPC_DME_APIs`` environment
    variable, then the parent of ``HPC_DM_UTILS`` when it ends with ``utils``.

    Raises:
        HpcDmeRepoError: if no path can be resolved or it is not a git repo.
    """
    repo = None
    if repo_override:
        repo = Path(repo_override).expanduser()
    elif os.environ.get("HPC_DME_APIs"):
        repo = Path(os.environ["HPC_DME_APIs"]).expanduser()
    elif os.environ.get("HPC_DM_UTILS"):
        dm_utils_path = Path(os.environ["HPC_DM_UTILS"]).expanduser()
        if dm_utils_path.name == "utils":
            repo = dm_utils_path.parent

    if repo is None:
        raise HpcDmeRepoError(
            "could not locate the HPC_DME_APIs repository.",
            hint=(
                "pass --repo /path/to/HPC_DME_APIs, set HPC_DME_APIs to the repo "
                "path, or set HPC_DM_UTILS to <HPC_DME_APIs>/utils."
            ),
            exit_code=2,
        )
    if not (repo / ".git").exists():
        raise HpcDmeRepoError(f"not a git repository: {repo}", exit_code=2)
    return repo


def fetch_release_refs(repo: Path, remote: str = DEFAULT_REMOTE) -> None:
    """Fetch ``master`` and every ``releases/*`` branch from ``remote``.

    Explicit refspecs are used so this also works in single-branch clones,
    whose configured fetch refspec only covers the originally cloned branch.

    Raises:
        HpcDmeRepoError: if the fetch fails.
    """
    refspecs = [
        f"+refs/heads/{MAINLINE_BRANCH}:refs/remotes/{remote}/{MAINLINE_BRANCH}",
        f"+refs/heads/{RELEASE_PREFIX}*:refs/remotes/{remote}/{RELEASE_PREFIX}*",
    ]
    run_git(repo, ["fetch", "--prune", "--no-tags", remote, *refspecs], check=True)


def list_release_branches(repo: Path, remote: str = DEFAULT_REMOTE) -> list:
    """Return ``(version, name, sha)`` for fetched ``releases/X.Y.Z`` branches.

    The list is sorted numerically, newest version first, so ``3.10.0`` sorts
    above ``3.9.0``.
    """
    proc = run_git(
        repo,
        [
            "for-each-ref",
            "--format=%(refname:lstrip=3) %(objectname)",
            f"refs/remotes/{remote}/{RELEASE_PREFIX}",
        ],
        check=True,
    )
    releases = []
    for line in proc.stdout.splitlines():
        name, _, sha = line.partition(" ")
        version = parse_release_version(name)
        if version is not None:
            releases.append((version, name, sha))
    return sorted(releases, reverse=True)


def latest_stable_release(repo: Path, remote: str = DEFAULT_REMOTE) -> SyncTarget:
    """Return the highest-versioned release branch already merged into master.

    Assumes :func:`fetch_release_refs` has been called.

    Raises:
        HpcDmeRepoError: if ``master`` is missing or no release is merged.
    """
    mainline = f"refs/remotes/{remote}/{MAINLINE_BRANCH}"
    if run_git(repo, ["rev-parse", "--verify", "--quiet", mainline]).returncode:
        raise HpcDmeRepoError(f"remote branch {remote}/{MAINLINE_BRANCH} not found.")

    stable = None
    for version, name, sha in list_release_branches(repo, remote):
        if is_ancestor(repo, sha, mainline):
            stable = SyncTarget(
                name=name, kind="branch", sha=sha, version=version, pinned=False
            )
            break

    if stable is None:
        raise HpcDmeRepoError(
            f"no {RELEASE_PREFIX}X.Y.Z branch on {remote} is merged into "
            f"{MAINLINE_BRANCH}.",
            hint="pass --ref <tag-or-branch> to choose a ref explicitly.",
        )
    return stable


def fetch_requested_ref(
    repo: Path, ref: str, remote: str = DEFAULT_REMOTE
) -> SyncTarget:
    """Fetch a user-requested branch or tag from ``remote`` and describe it.

    Raises:
        HpcDmeRepoError: if the ref does not exist or is ambiguous.
    """
    name = normalize_ref(ref)
    proc = run_git(
        repo,
        ["ls-remote", remote, f"refs/heads/{name}", f"refs/tags/{name}"],
        check=True,
    )
    remote_refs = {line.split("\t", 1)[1] for line in proc.stdout.splitlines()}
    is_branch = f"refs/heads/{name}" in remote_refs
    is_tag = f"refs/tags/{name}" in remote_refs

    if is_branch and is_tag:
        raise HpcDmeRepoError(
            f"'{name}' is both a branch and a tag on {remote}.",
            hint="remove the ambiguity upstream or choose a different ref.",
            exit_code=2,
        )
    if not (is_branch or is_tag):
        raise HpcDmeRepoError(
            f"no branch or tag named '{name}' on {remote}.",
            hint="check the name, e.g. releases/3.30.1, 3.30.1, or an existing tag.",
            exit_code=2,
        )

    kind = "branch" if is_branch else "tag"
    if is_branch:
        local_ref = f"refs/remotes/{remote}/{name}"
        refspec = f"+refs/heads/{name}:{local_ref}"
    else:
        local_ref = f"refs/tags/{name}"
        refspec = f"+refs/tags/{name}:{local_ref}"
    run_git(repo, ["fetch", "--no-tags", remote, refspec], check=True)
    sha = run_git(repo, ["rev-parse", f"{local_ref}^{{commit}}"], check=True)
    sha = sha.stdout.strip()

    version = parse_release_version(name)
    if version is None:
        version = jar_version_at(repo, sha)
    return SyncTarget(name=name, kind=kind, sha=sha, version=version, pinned=True)


def resolve_sync_target(
    repo: Path, ref: str = "", remote: str = DEFAULT_REMOTE
) -> SyncTarget:
    """Fetch from ``remote`` and return the ref the local clone should match.

    Uses ``ref`` when given; otherwise the latest stable release branch.
    """
    target = None
    if ref:
        target = fetch_requested_ref(repo, ref, remote)
    else:
        fetch_release_refs(repo, remote)
        target = latest_stable_release(repo, remote)
    return target


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` is reachable from ``descendant``."""
    proc = run_git(repo, ["merge-base", "--is-ancestor", ancestor, descendant])
    return proc.returncode == 0


def head_sha(repo: Path) -> str:
    """Return the commit SHA of ``HEAD``."""
    return run_git(repo, ["rev-parse", "HEAD"], check=True).stdout.strip()


def current_branch(repo: Path) -> str:
    """Return the checked-out branch name, or ``HEAD`` when detached."""
    proc = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], check=True)
    return proc.stdout.strip()


def _parse_jar_version(text: str) -> Version | None:
    match = _JAR_VERSION_RE.search(text)
    version = None
    if match:
        version = tuple(int(part) for part in match.groups())
    return version


def jar_version_at(repo: Path, rev: str) -> Version | None:
    """Return the hpc-cli jar version listed in ``utils/version`` at ``rev``."""
    proc = run_git(repo, ["show", f"{rev}:utils/version"])
    version = None
    if proc.returncode == 0:
        version = _parse_jar_version(proc.stdout)
    return version


def current_release_version(repo: Path) -> Version | None:
    """Return the release version of the local checkout.

    Uses the ``releases/X.Y.Z`` branch name when on one; otherwise falls back
    to the jar version in ``utils/version``. Patch releases do not always bump
    the jar (``releases/3.29.1`` ships ``hpc-cli-3.29.0.jar``), so the branch
    name is preferred.
    """
    version = parse_release_version(current_branch(repo))
    if version is None:
        version = jar_version_at(repo, "HEAD")
    return version


def same_tree(repo: Path, rev_a: str, rev_b: str) -> bool:
    """Return whether two revisions have identical file content."""
    trees = []
    for rev in (rev_a, rev_b):
        proc = run_git(repo, ["rev-parse", f"{rev}^{{tree}}"])
        trees.append(proc.stdout.strip() if proc.returncode == 0 else None)
    return trees[0] is not None and trees[0] == trees[1]


def has_tracked_changes(repo: Path) -> bool:
    """Return whether tracked files have uncommitted changes."""
    proc = run_git(repo, ["status", "--porcelain", "--untracked-files=no"], check=True)
    return bool(proc.stdout.strip())


def _set_upstream(repo: Path, branch: str, remote: str) -> None:
    """Make ``branch`` track ``remote``'s branch of the same name.

    Written directly to git config because ``git branch --set-upstream-to``
    rejects remote-tracking refs outside the remote's configured fetch
    refspec, which is the case in single-branch clones.
    """
    run_git(repo, ["config", f"branch.{branch}.remote", remote], check=True)
    run_git(
        repo, ["config", f"branch.{branch}.merge", f"refs/heads/{branch}"], check=True
    )


def checkout_target(
    repo: Path, target: SyncTarget, remote: str = DEFAULT_REMOTE
) -> None:
    """Move the local clone to ``target`` without creating merge commits.

    Branches are checked out as a local branch tracking ``remote`` and
    fast-forwarded; tags are checked out as a detached ``HEAD``.

    Raises:
        HpcDmeRepoError: if a local branch has commits not in the target.
    """
    local_ref = f"refs/heads/{target.name}"
    has_local_branch = (
        target.kind == "branch"
        and run_git(repo, ["rev-parse", "--verify", "--quiet", local_ref]).returncode
        == 0
    )
    if has_local_branch and not is_ancestor(repo, local_ref, target.sha):
        raise HpcDmeRepoError(
            f"local branch {target.name} has commits that are not on "
            f"{remote}/{target.name}.",
            hint=(
                f"inspect them with 'git log {remote}/{target.name}..{target.name}', "
                "then move or drop them before retrying."
            ),
        )

    if target.kind == "tag":
        run_git(repo, ["switch", "--detach", target.sha], check=True)
    elif has_local_branch:
        run_git(repo, ["switch", target.name], check=True)
        run_git(repo, ["merge", "--ff-only", target.sha], check=True)
        _set_upstream(repo, target.name, remote)
    else:
        run_git(repo, ["switch", "-c", target.name, target.sha], check=True)
        _set_upstream(repo, target.name, remote)
