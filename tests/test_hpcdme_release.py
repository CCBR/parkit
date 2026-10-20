"""Tests for HPC_DME_APIs release-branch resolution, checkapisync and syncapi.

Each test builds a local "upstream" repository that mimics CBIIT/HPC_DME_APIs:
``releases/X.Y.Z`` branches, some merged into ``master`` and some not, plus
oddly named branches that must be ignored. The clone under test is a
single-branch clone of an old release, like a typical user setup.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("HOSTNAME", "helix.nih.gov")
os.environ.setdefault("HPC_DM_UTILS", "/tmp")
os.environ.setdefault("HPC_DM_JAVA_VERSION", "23.0.2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parkit.src import syncapi as syncapi_module
from parkit.src.checkapisync import check_hpc_dme_apis_sync
from parkit.src.hpcdme_release import (
    HpcDmeRepoError,
    current_branch,
    current_release_version,
    fetch_release_refs,
    head_sha,
    latest_stable_release,
    list_release_branches,
    normalize_ref,
    parse_release_version,
    requested_ref,
    resolve_repo_path,
    resolve_sync_target,
)

GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
}


def git(repo, *args):
    """Run git in ``repo`` and return stripped stdout."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    )
    return proc.stdout.strip()


def commit_release(repo, version, jar_version=None):
    """Commit a ``utils/version`` file naming the hpc-cli jar."""
    utils = repo / "utils"
    utils.mkdir(exist_ok=True)
    (utils / "version").write_text(
        f"hpc.jar.version=hpc-cli-{jar_version or version}.jar\n"
    )
    (utils / "functions").write_text("# functions\n")
    (repo / "RELEASE").write_text(f"{version}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"release {version}")


def create_release(repo, version, merge, jar_version=None):
    """Create ``releases/<version>`` from master, optionally merging it back."""
    branch = f"releases/{version}"
    git(repo, "switch", "-q", "-c", branch, "master")
    commit_release(repo, version, jar_version)
    git(repo, "switch", "-q", "master")
    if merge:
        git(repo, "merge", "-q", "--no-ff", "-m", f"Merge {branch}", branch)


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch):
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("HPC_DME_APIs_REF", raising=False)


@pytest.fixture
def upstream(tmp_path):
    """Upstream repo: stable 3.10.1 (merged), newer 3.11.0 (unmerged)."""
    repo = tmp_path / "upstream"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "master")
    commit_release(repo, "3.8.0")
    create_release(repo, "3.9.0", merge=True)
    create_release(repo, "3.10.0", merge=True)
    # Patch releases may keep the previous jar, as releases/3.29.1 does upstream.
    create_release(repo, "3.10.1", merge=True, jar_version="3.10.0")
    create_release(repo, "3.11.0", merge=False)
    git(repo, "branch", "releases/3.12.0-candidate")
    git(repo, "branch", "releases/CICD-pipeline-test")
    git(repo, "branch", "releeases/99.0.0")
    git(repo, "tag", "-a", "v3.9.0", "-m", "tag", "releases/3.9.0")
    return repo


@pytest.fixture
def clone(tmp_path, upstream):
    """Single-branch clone checked out on the old releases/3.9.0 branch."""
    path = tmp_path / "HPC_DME_APIs"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--single-branch",
            "--branch",
            "releases/3.9.0",
            str(upstream),
            str(path),
        ],
        check=True,
        env={**os.environ, **GIT_ENV},
    )
    return path


@pytest.fixture
def no_token(monkeypatch):
    """Skip the interactive dm_generate_token step."""
    calls = []
    monkeypatch.setattr(syncapi_module, "_generate_token", calls.append)
    return calls


@pytest.mark.parametrize(
    "name, expected",
    [
        ("releases/3.30.1", (3, 30, 1)),
        ("releases/3.9.0", (3, 9, 0)),
        ("releases/1.5.2-candidate", None),
        ("releases/CICD-pipeline-test", None),
        ("releeases/3.3.0", None),
        ("master", None),
    ],
)
def test_parse_release_version(name, expected):
    assert parse_release_version(name) == expected


def test_normalize_ref_and_requested_ref(monkeypatch):
    assert normalize_ref("3.31.0") == "releases/3.31.0"
    assert normalize_ref("releases/3.31.0") == "releases/3.31.0"
    assert normalize_ref("v3.9.0") == "v3.9.0"
    monkeypatch.setenv("HPC_DME_APIs_REF", "3.30.2")
    assert requested_ref() == "3.30.2"
    assert requested_ref("master") == "master"


def test_list_release_branches_sorts_numerically_and_filters(clone):
    fetch_release_refs(clone)
    names = [name for _, name, _ in list_release_branches(clone)]
    assert names == [
        "releases/3.11.0",
        "releases/3.10.1",
        "releases/3.10.0",
        "releases/3.9.0",
    ]


def test_latest_stable_release_skips_unmerged(clone, upstream):
    fetch_release_refs(clone)
    stable = latest_stable_release(clone)
    assert stable.name == "releases/3.10.1"
    assert stable.sha == git(upstream, "rev-parse", "releases/3.10.1")
    assert stable.pinned is False


def test_resolve_sync_target_pinned_branch_tag_and_missing(clone, upstream):
    branch = resolve_sync_target(clone, "3.11.0")
    assert (branch.name, branch.kind, branch.version) == (
        "releases/3.11.0",
        "branch",
        (3, 11, 0),
    )
    tag = resolve_sync_target(clone, "v3.9.0")
    assert tag.kind == "tag"
    assert tag.sha == git(upstream, "rev-parse", "releases/3.9.0")
    assert tag.version == (3, 9, 0)
    with pytest.raises(HpcDmeRepoError, match="no branch or tag"):
        resolve_sync_target(clone, "does-not-exist")


def test_resolve_repo_path_without_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("HPC_DME_APIs", raising=False)
    monkeypatch.delenv("HPC_DM_UTILS", raising=False)
    with pytest.raises(HpcDmeRepoError) as excinfo:
        resolve_repo_path()
    assert excinfo.value.exit_code == 2

    monkeypatch.setenv("HPC_DM_UTILS", str(tmp_path / "not_utils"))
    with pytest.raises(HpcDmeRepoError):
        resolve_repo_path()


def test_resolve_repo_path_from_hpc_dm_utils(monkeypatch, clone):
    monkeypatch.delenv("HPC_DME_APIs", raising=False)
    monkeypatch.setenv("HPC_DM_UTILS", str(clone / "utils"))
    assert resolve_repo_path() == clone


def test_checkapisync_reports_old_release_out_of_sync(clone, capsys):
    assert check_hpc_dme_apis_sync(str(clone)) == 1
    out = capsys.readouterr().out
    assert "older than releases/3.10.1" in out


def test_syncapi_moves_to_latest_stable_release(clone, upstream, no_token):
    assert syncapi_module.syncapi(str(clone)) == 0
    assert current_branch(clone) == "releases/3.10.1"
    assert head_sha(clone) == git(upstream, "rev-parse", "releases/3.10.1")
    assert current_release_version(clone) == (3, 10, 1)
    assert git(clone, "config", "branch.releases/3.10.1.remote") == "origin"
    assert (
        git(clone, "config", "branch.releases/3.10.1.merge")
        == "refs/heads/releases/3.10.1"
    )
    assert len(no_token) == 1
    assert check_hpc_dme_apis_sync(str(clone)) == 0


def test_syncapi_fast_forwards_same_release(clone, upstream, no_token):
    assert syncapi_module.syncapi(str(clone)) == 0
    git(upstream, "switch", "-q", "releases/3.10.1")
    (upstream / "hotfix.txt").write_text("fix\n")
    git(upstream, "add", "-A")
    git(upstream, "commit", "-q", "-m", "hotfix")
    git(upstream, "switch", "-q", "master")
    git(upstream, "merge", "-q", "--no-ff", "-m", "merge hotfix", "releases/3.10.1")

    assert check_hpc_dme_apis_sync(str(clone)) == 1
    assert syncapi_module.syncapi(str(clone)) == 0
    assert head_sha(clone) == git(upstream, "rev-parse", "releases/3.10.1")


def test_syncapi_refuses_dirty_tracked_files(clone, no_token):
    before = head_sha(clone)
    (clone / "utils" / "functions").write_text("# local edit\n")
    assert syncapi_module.syncapi(str(clone)) == 1
    assert head_sha(clone) == before
    assert no_token == []


def test_syncapi_keeps_untracked_files(clone, no_token):
    (clone / "utils" / "hpcdme.properties").write_text("user settings\n")
    assert syncapi_module.syncapi(str(clone)) == 0
    assert (clone / "utils" / "hpcdme.properties").read_text() == "user settings\n"


def test_newer_local_release_is_not_downgraded(clone, upstream, no_token):
    assert syncapi_module.syncapi(str(clone), ref="3.11.0") == 0
    newer = head_sha(clone)
    assert newer == git(upstream, "rev-parse", "releases/3.11.0")

    assert check_hpc_dme_apis_sync(str(clone)) == 0
    assert syncapi_module.syncapi(str(clone)) == 0
    assert head_sha(clone) == newer


def test_pinned_ref_from_env_allows_downgrade(clone, upstream, no_token, monkeypatch):
    assert syncapi_module.syncapi(str(clone)) == 0
    monkeypatch.setenv("HPC_DME_APIs_REF", "3.10.0")
    assert check_hpc_dme_apis_sync(str(clone)) == 1
    assert syncapi_module.syncapi(str(clone)) == 0
    assert current_branch(clone) == "releases/3.10.0"
    assert check_hpc_dme_apis_sync(str(clone)) == 0


def test_pinned_tag_checks_out_detached(clone, upstream, no_token):
    assert syncapi_module.syncapi(str(clone)) == 0
    assert syncapi_module.syncapi(str(clone), ref="v3.9.0") == 0
    assert current_branch(clone) == "HEAD"
    assert head_sha(clone) == git(upstream, "rev-parse", "v3.9.0^{commit}")
    assert check_hpc_dme_apis_sync(str(clone), ref="v3.9.0") == 0


def test_syncapi_refuses_local_commits_on_target_branch(clone, upstream, no_token):
    git(clone, "fetch", "-q", "origin", "releases/3.10.1:releases/3.10.1")
    git(clone, "switch", "-q", "releases/3.10.1")
    (clone / "local.txt").write_text("local\n")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "local work")
    git(clone, "switch", "-q", "releases/3.9.0")

    assert syncapi_module.syncapi(str(clone)) == 1
    assert current_branch(clone) == "releases/3.9.0"
    assert no_token == []
