"""Tests for the staging-directory integration in ``parkit.projark``."""

import os
import sys
from collections import namedtuple
from pathlib import Path

import pytest

os.environ.setdefault("HOSTNAME", "helix.nih.gov")
os.environ.setdefault("HPC_DM_UTILS", "/tmp")
os.environ.setdefault("HPC_DM_JAVA_VERSION", "23.0.2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parkit import projark
from parkit.src import staging
from parkit.src.staging import ENV_VAR, MARKER_NAME, StagingError

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])
TINY_FREE = 1024
HUGE_FREE = 1024**5


def _fake_disk_usage(free):
    """Return a ``shutil.disk_usage`` replacement reporting ``free`` bytes."""

    def _disk_usage(_path):
        return DiskUsage(total=free * 2, used=free, free=free)

    return _disk_usage


@pytest.fixture
def gates(monkeypatch):
    """Disable host/session/sync gates shared by deposit and retrieve."""
    monkeypatch.setattr(projark, "_run_sync_gate", lambda: True)
    monkeypatch.setattr(projark, "_require_helix", lambda: None)
    monkeypatch.setattr(projark, "_require_terminal_multiplexer", lambda: None)
    monkeypatch.setattr(projark, "_print_hpcdme_properties", lambda: None)
    monkeypatch.setattr(projark, "_check_no_proxy_settings", lambda: True)
    monkeypatch.setenv("USER", "testuser")


@pytest.fixture
def collection_calls(monkeypatch):
    """Record calls to ``_ensure_deposit_collections`` instead of touching HPC-DME."""
    calls = []

    def _fake(base_collection, datatype, project_number):
        calls.append((base_collection, datatype, project_number))
        return f"{base_collection}/{datatype}"

    monkeypatch.setattr(projark, "_ensure_deposit_collections", _fake)
    return calls


@pytest.fixture
def source_dir(tmp_path):
    """Create a small source tree to archive."""
    src = tmp_path / "source" / "project_data"
    src.mkdir(parents=True)
    (src / "file.txt").write_text("hello\n")
    return src


@pytest.fixture
def staging_base(tmp_path, monkeypatch):
    """Create a staging base and point ``$PROJARK_STAGING_DIR`` at it."""
    base = tmp_path / "staging"
    base.mkdir()
    monkeypatch.setenv(ENV_VAR, str(base))
    return base


def _deposit_args(source, *extra):
    return projark._build_parser().parse_args(
        ["deposit", "-f", str(source), "-p", "1234", *extra]
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_deposit_parser_staging_dir():
    args = projark._build_parser().parse_args(
        ["deposit", "-f", "X", "-p", "1234", "--staging-dir", "/some"]
    )
    assert args.staging_dir == "/some"


def test_deposit_parser_staging_dir_default():
    args = projark._build_parser().parse_args(["deposit", "-f", "X", "-p", "1234"])
    assert args.staging_dir == ""
    assert args.cleanup is True


def test_retrieve_parser_folder_and_staging_dir_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        projark._build_parser().parse_args(
            ["retrieve", "-p", "1234", "--folder", "a", "--staging-dir", "b"]
        )
    assert "not allowed with argument" in capsys.readouterr().err


def test_retrieve_parser_staging_dir():
    args = projark._build_parser().parse_args(
        ["retrieve", "-p", "1234", "--staging-dir", "b"]
    )
    assert args.staging_dir == "b"
    assert args.folder == ""


def test_retrieve_parser_defaults():
    args = projark._build_parser().parse_args(["retrieve", "-p", "1234"])
    assert args.staging_dir == ""
    assert args.folder == ""


# ---------------------------------------------------------------------------
# Deposit preflight
# ---------------------------------------------------------------------------


def test_deposit_insufficient_space_aborts_before_collections(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(TINY_FREE))
    with pytest.raises(StagingError):
        projark._run_deposit(_deposit_args(source_dir))
    assert collection_calls == []
    assert not (staging_base / "CCBR-1234").exists()


def test_deposit_nonpositive_split_size_aborts_before_collections(
    gates, collection_calls, source_dir, staging_base
):
    rc = projark._run_deposit(_deposit_args(source_dir, "--split-size-gb", "0"))
    assert rc == 1
    assert collection_calls == []


def test_deposit_overlap_aborts_before_collections(
    gates, collection_calls, tmp_path, monkeypatch
):
    source = tmp_path / "CCBR-1234"
    source.mkdir()
    (source / "data.txt").write_text("payload\n")
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    with pytest.raises(StagingError):
        projark._run_deposit(_deposit_args(source))
    assert collection_calls == []
    assert (source / "data.txt").read_text() == "payload\n"


def test_deposit_unmarked_existing_root_aborts_before_collections(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    existing = staging_base / "CCBR-1234" / "Analysis"
    existing.mkdir(parents=True)
    keep = existing / "keep.txt"
    keep.write_text("do not delete\n")
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    with pytest.raises(StagingError):
        projark._run_deposit(_deposit_args(source_dir))
    assert collection_calls == []
    assert keep.read_text() == "do not delete\n"
    assert not (staging_base / "CCBR-1234" / MARKER_NAME).exists()


def _patch_deposit_workers(monkeypatch, dm_calls, root):
    """Replace tar/split/md5/transfer helpers with lightweight fakes."""

    def _fake_createtar(source, tar_path):
        Path(tar_path).write_bytes(b"tar")
        Path(f"{tar_path}.filelist").write_text("file.txt\n")

    def _fake_run_dm_cmd(dm_cmd, errormsg="", **_kwargs):
        dm_calls.append((dm_cmd, (root / MARKER_NAME).is_file()))

    monkeypatch.setattr(projark, "createtar", _fake_createtar)
    monkeypatch.setattr(projark, "_split_if_needed", lambda tar_path, size: [tar_path])
    monkeypatch.setattr(projark, "_write_md5_files", lambda directory: None)
    monkeypatch.setattr(projark, "_resolve_tarname", lambda name, coll: name)
    monkeypatch.setattr(projark, "run_dm_cmd", _fake_run_dm_cmd)
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))


def test_deposit_happy_path_with_cleanup(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    root = staging_base / "CCBR-1234"
    dm_calls = []
    _patch_deposit_workers(monkeypatch, dm_calls, root)

    rc = projark._run_deposit(_deposit_args(source_dir))

    assert rc == 0
    assert collection_calls == [
        ("/CCBR_Archive/GRIDFTP/Project_CCBR-1234", "Analysis", "1234")
    ]
    assert len(dm_calls) == 1
    cmd, marker_present = dm_calls[0]
    assert "dm_register_directory" in cmd
    assert f"{root / 'Analysis'}/" in cmd
    assert marker_present
    assert not root.exists()


def test_deposit_happy_path_no_cleanup_keeps_staging(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    root = staging_base / "CCBR-1234"
    dm_calls = []
    _patch_deposit_workers(monkeypatch, dm_calls, root)

    rc = projark._run_deposit(_deposit_args(source_dir, "-k"))

    assert rc == 0
    assert (root / MARKER_NAME).is_file()
    assert (root / "Analysis" / "ccbr1234.tar").is_file()
    assert (root / "Analysis" / "ccbr1234.tar.filelist").is_file()


def test_deposit_staging_dir_cli_overrides_env(
    gates, collection_calls, source_dir, staging_base, tmp_path, monkeypatch
):
    cli_base = tmp_path / "cli_staging"
    cli_base.mkdir()
    root = cli_base / "CCBR-1234"
    dm_calls = []
    _patch_deposit_workers(monkeypatch, dm_calls, root)

    rc = projark._run_deposit(
        _deposit_args(source_dir, "-k", "--staging-dir", str(cli_base))
    )

    assert rc == 0
    assert (root / "Analysis" / "ccbr1234.tar").is_file()
    assert not (staging_base / "CCBR-1234").exists()


def test_deposit_marked_existing_root_is_replaced(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    root = staging_base / "CCBR-1234"
    dm_calls = []
    _patch_deposit_workers(monkeypatch, dm_calls, root)
    assert projark._run_deposit(_deposit_args(source_dir, "-k")) == 0
    stale = root / "Analysis" / "stale.txt"
    stale.write_text("old\n")

    assert projark._run_deposit(_deposit_args(source_dir, "-k")) == 0
    assert not stale.exists()
    assert (root / MARKER_NAME).is_file()


# ---------------------------------------------------------------------------
# Retrieve
# ---------------------------------------------------------------------------

COLLECTION = "/CCBR_Archive/GRIDFTP/Project_CCBR-1234/Analysis"


@pytest.fixture
def retrieve_env(gates, monkeypatch):
    """Fake the HPC-DME side of ``projark retrieve`` and record downloads."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr(
        projark,
        "_ensure_retrieve_collections",
        lambda base_collection, datatype: f"{base_collection}/{datatype}",
    )
    objects = [
        (f"{COLLECTION}/ccbr1234.tar", 50 * 1024**4, "user", "2026-01-01"),
        (f"{COLLECTION}/ccbr1234.tar.filelist", 1024, "user", "2026-01-01"),
    ]
    monkeypatch.setattr(projark, "query_all_dataobjects", lambda coll: objects)
    dm_calls = []
    monkeypatch.setattr(
        projark,
        "run_dm_cmd",
        lambda dm_cmd, errormsg="", **_kwargs: dm_calls.append(dm_cmd),
    )
    return dm_calls


def _retrieve_args(*extra):
    return projark._build_parser().parse_args(["retrieve", "-p", "1234", *extra])


@pytest.mark.parametrize("filenames", [[], ["-n", "ccbr1234.tar"]])
def test_retrieve_insufficient_space_aborts_before_download(
    retrieve_env, tmp_path, monkeypatch, filenames
):
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(TINY_FREE))
    with pytest.raises(StagingError):
        projark._run_retrieve(
            _retrieve_args("--staging-dir", str(tmp_path), *filenames)
        )
    assert retrieve_env == []


def test_retrieve_staging_dir_target_without_marker(
    retrieve_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    rc = projark._run_retrieve(
        _retrieve_args("--staging-dir", str(tmp_path), "-n", "ccbr1234.tar.filelist")
    )
    assert rc == 0
    target = tmp_path.resolve() / "CCBR-1234" / "Analysis"
    assert target.is_dir()
    assert not (tmp_path / "CCBR-1234" / MARKER_NAME).exists()
    assert len(retrieve_env) == 1
    assert "dm_download_dataobject" in retrieve_env[0]
    assert str(target) in retrieve_env[0]


def test_retrieve_env_var_default_full_collection(retrieve_env, tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    rc = projark._run_retrieve(_retrieve_args())
    assert rc == 0
    base_local = tmp_path.resolve() / "CCBR-1234"
    assert (base_local / "Analysis").is_dir()
    assert not (base_local / MARKER_NAME).exists()
    assert len(retrieve_env) == 1
    assert "dm_download_collection" in retrieve_env[0]
    assert str(base_local) in retrieve_env[0]


def test_retrieve_folder_works_without_user(retrieve_env, tmp_path, monkeypatch):
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    out = tmp_path / "out"
    rc = projark._run_retrieve(_retrieve_args("--folder", str(out)))
    assert rc == 0
    assert (out / "Analysis").is_dir()
    assert len(retrieve_env) == 1


# ---------------------------------------------------------------------------
# Review fixes: tarname preflight, reclaimable space, retrieve guard
# ---------------------------------------------------------------------------


def test_deposit_tarname_with_slash_aborts_before_collections(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    rc = projark._run_deposit(_deposit_args(source_dir, "--tarname", "a/b.tar"))
    assert rc == 1
    assert collection_calls == []
    assert not (staging_base / "CCBR-1234").exists()


def test_deposit_rerun_counts_previous_marked_root_as_free(
    gates, collection_calls, source_dir, staging_base, monkeypatch
):
    root = staging_base / "CCBR-1234"
    staging.prepare_staging_root(root, "Analysis", {"projectnumber": "1234"})
    (root / "Analysis" / "old.tar").write_bytes(os.urandom(64 * 1024))
    reclaim = staging.reclaimable_bytes(root)
    assert reclaim > 0
    tar_bytes, filelist_bytes = staging.estimate_staging_bytes(source_dir)
    required = staging.deposit_required_bytes(
        tar_bytes, int(projark.DEFAULT_SPLIT_SIZE_GB * 1024**3), filelist_bytes
    )
    free = required - reclaim // 2
    dm_calls = []
    _patch_deposit_workers(monkeypatch, dm_calls, root)
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(free))
    monkeypatch.setattr(projark.shutil, "disk_usage", _fake_disk_usage(free))

    rc = projark._run_deposit(_deposit_args(source_dir, "-k"))

    assert rc == 0
    assert collection_calls
    assert not (root / "Analysis" / "old.tar").exists()


@pytest.mark.parametrize("how", ["folder", "nested_folder", "staging_dir", "env"])
def test_retrieve_refuses_marked_deposit_staging_folder(
    retrieve_env, tmp_path, monkeypatch, how
):
    root = tmp_path / "CCBR-1234"
    staging.prepare_staging_root(root, "Analysis", {"projectnumber": "1234"})
    monkeypatch.setattr(staging.shutil, "disk_usage", _fake_disk_usage(HUGE_FREE))
    extra = []
    if how == "folder":
        extra = ["--folder", str(root)]
    elif how == "nested_folder":
        extra = ["--folder", str(root / "Analysis")]
    elif how == "staging_dir":
        extra = ["--staging-dir", str(tmp_path)]
    else:
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
    with pytest.raises(StagingError, match="deposit staging folder"):
        projark._run_retrieve(_retrieve_args(*extra))
    assert retrieve_env == []
