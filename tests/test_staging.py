"""Tests for parkit.src.staging (projark staging-area helpers)."""

import json
import os
import shutil
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import pytest

os.environ.setdefault("HOSTNAME", "helix.nih.gov")
os.environ.setdefault("HPC_DM_UTILS", "/tmp")
os.environ.setdefault("HPC_DM_JAVA_VERSION", "23.0.2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parkit.src import staging
from parkit.src.staging import (
    ENV_VAR,
    GIB,
    MARKER_NAME,
    StagingError,
    assert_free_space,
    assert_no_overlap,
    check_existing_root,
    deposit_required_bytes,
    estimate_tar_bytes,
    prepare_staging_root,
    remove_staging_root,
    resolve_staging_base,
    retrieve_required_bytes,
    staging_root,
)

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])


# --------------------------------------------------------------------------
# resolve_staging_base
# --------------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Isolate USER / PROJARK_STAGING_DIR and the default parent."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setenv("USER", "testuser")
    monkeypatch.setattr(staging, "DEFAULT_PARENT", tmp_path / "scratch")
    return tmp_path


def test_resolve_default_creates_user_dir(clean_env):
    base, is_default = resolve_staging_base("")
    expected = (clean_env / "scratch" / "testuser").resolve()
    assert base == expected
    assert is_default is True
    assert base.is_dir()


def test_resolve_env_over_default(clean_env, monkeypatch):
    env_dir = clean_env / "envdir"
    env_dir.mkdir()
    monkeypatch.setenv(ENV_VAR, str(env_dir))
    base, is_default = resolve_staging_base()
    assert base == env_dir.resolve()
    assert is_default is False
    assert not (clean_env / "scratch").exists()


def test_resolve_blank_env_falls_back_to_default(clean_env, monkeypatch):
    monkeypatch.setenv(ENV_VAR, "   ")
    base, is_default = resolve_staging_base("")
    assert is_default is True
    assert base.name == "testuser"


def test_resolve_cli_over_env(clean_env, monkeypatch):
    env_dir = clean_env / "envdir"
    cli_dir = clean_env / "clidir"
    env_dir.mkdir()
    cli_dir.mkdir()
    monkeypatch.setenv(ENV_VAR, str(env_dir))
    base, is_default = resolve_staging_base(str(cli_dir))
    assert base == cli_dir.resolve()
    assert is_default is False


def test_resolve_expands_user(clean_env, monkeypatch):
    home = clean_env / "home"
    (home / "stage").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    base, _ = resolve_staging_base("~/stage")
    assert base == (home / "stage").resolve()


def test_resolve_custom_must_exist(clean_env):
    missing = clean_env / "nope"
    with pytest.raises(StagingError, match="does not exist"):
        resolve_staging_base(str(missing))
    assert not missing.exists()


def test_resolve_env_must_exist(clean_env, monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(clean_env / "nope"))
    with pytest.raises(StagingError, match="does not exist"):
        resolve_staging_base()


def test_resolve_custom_must_be_dir(clean_env):
    afile = clean_env / "afile"
    afile.write_text("x")
    with pytest.raises(StagingError, match="not a directory"):
        resolve_staging_base(str(afile))


def test_resolve_custom_must_be_writable(clean_env, monkeypatch):
    d = clean_env / "ro"
    d.mkdir()
    monkeypatch.setattr(staging.os, "access", lambda path, mode: False)
    with pytest.raises(StagingError, match="not writable"):
        resolve_staging_base(str(d))


def test_resolve_rejects_root(clean_env):
    with pytest.raises(StagingError, match="filesystem root"):
        resolve_staging_base("/")


def test_resolve_missing_user(clean_env, monkeypatch):
    monkeypatch.delenv("USER", raising=False)
    with pytest.raises(StagingError, match="USER"):
        resolve_staging_base("")


def test_resolve_empty_user(clean_env, monkeypatch):
    monkeypatch.setenv("USER", "")
    with pytest.raises(StagingError, match="USER"):
        resolve_staging_base("")


def test_staging_root(tmp_path):
    assert staging_root(tmp_path, "CCBR-1234") == tmp_path / "CCBR-1234"


# --------------------------------------------------------------------------
# assert_no_overlap
# --------------------------------------------------------------------------


def test_overlap_equal(tmp_path):
    with pytest.raises(StagingError, match="same folder"):
        assert_no_overlap(tmp_path / "x", tmp_path / "x")


def test_overlap_root_inside_source(tmp_path):
    source = tmp_path / "data"
    source.mkdir()
    with pytest.raises(StagingError, match="inside the source"):
        assert_no_overlap(source / "CCBR-1", source)


def test_overlap_source_inside_root(tmp_path):
    root = tmp_path / "CCBR-1"
    source = root / "analysis"
    source.mkdir(parents=True)
    with pytest.raises(StagingError, match="would delete the source"):
        assert_no_overlap(root, source)


def test_overlap_siblings_ok(tmp_path):
    source = tmp_path / "data" / "CCBR-1"
    source.mkdir(parents=True)
    assert_no_overlap(tmp_path / "stage" / "CCBR-1", source)
    # name prefix is not containment
    assert_no_overlap(tmp_path / "data" / "CCBR-10", source)


def test_overlap_via_symlink(tmp_path):
    source = tmp_path / "data"
    source.mkdir()
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(StagingError, match="inside the source"):
        assert_no_overlap(link / "CCBR-1", source)
    with pytest.raises(StagingError, match="same folder"):
        assert_no_overlap(link, source)


# --------------------------------------------------------------------------
# check_existing_root / prepare_staging_root / remove_staging_root
# --------------------------------------------------------------------------


def test_check_existing_root_missing_ok(tmp_path):
    check_existing_root(tmp_path / "CCBR-1")


def test_check_existing_root_unmarked(tmp_path):
    root = tmp_path / "CCBR-1"
    root.mkdir()
    with pytest.raises(StagingError, match="not created by projark deposit"):
        check_existing_root(root)


def test_check_existing_root_is_file(tmp_path):
    root = tmp_path / "CCBR-1"
    root.write_text("x")
    with pytest.raises(StagingError, match="not a directory"):
        check_existing_root(root)


def test_check_existing_root_symlink(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / MARKER_NAME).write_text("{}")
    root = tmp_path / "CCBR-1"
    root.symlink_to(target)
    with pytest.raises(StagingError, match="symbolic link"):
        check_existing_root(root)


def test_prepare_fresh(tmp_path):
    root = tmp_path / "CCBR-1"
    meta = {"projectnumber": "1", "datatype": "Analysis", "source": "/x"}
    out = prepare_staging_root(root, "Analysis", meta)
    assert out == root / "Analysis"
    assert out.is_dir()
    marker = json.loads((root / MARKER_NAME).read_text())
    assert marker["projectnumber"] == "1"
    assert marker["datatype"] == "Analysis"
    assert marker["source"] == "/x"
    assert "created_at" in marker
    assert "T" in marker["created_at"]
    assert marker["created_at"][-6] in "+-"


def test_prepare_existing_marked_is_wiped(tmp_path):
    root = tmp_path / "CCBR-1"
    prepare_staging_root(root, "Analysis", {})
    (root / "Analysis" / "old.tar").write_text("old")
    (root / "Other").mkdir()
    out = prepare_staging_root(root, "Raw", {"datatype": "Raw"})
    assert out == root / "Raw"
    assert not (root / "Analysis").exists()
    assert not (root / "Other").exists()
    assert (root / MARKER_NAME).is_file()


def test_prepare_existing_unmarked_untouched(tmp_path):
    root = tmp_path / "CCBR-1"
    root.mkdir()
    keep = root / "precious.txt"
    keep.write_text("keep me")
    with pytest.raises(StagingError, match="not created by projark deposit"):
        prepare_staging_root(root, "Analysis", {})
    assert keep.read_text() == "keep me"
    assert sorted(p.name for p in root.iterdir()) == ["precious.txt"]


def test_prepare_root_is_file(tmp_path):
    root = tmp_path / "CCBR-1"
    root.write_text("x")
    with pytest.raises(StagingError, match="not a directory"):
        prepare_staging_root(root, "Analysis", {})
    assert root.read_text() == "x"


def test_remove_missing_noop(tmp_path):
    remove_staging_root(tmp_path / "CCBR-1")


def test_remove_unmarked_refuses(tmp_path):
    root = tmp_path / "CCBR-1"
    root.mkdir()
    (root / "f").write_text("x")
    with pytest.raises(StagingError, match="not created by projark deposit"):
        remove_staging_root(root)
    assert (root / "f").exists()


def test_remove_marked(tmp_path):
    root = tmp_path / "CCBR-1"
    prepare_staging_root(root, "Analysis", {})
    (root / "Analysis" / "a.tar").write_text("x")
    remove_staging_root(root)
    assert not root.exists()


# --------------------------------------------------------------------------
# estimate_tar_bytes
# --------------------------------------------------------------------------


def _real_tar_size(source: Path, out: Path) -> int:
    subprocess.run(
        ["tar", "cf", str(out), str(source)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out.stat().st_size


def _build_tree(source: Path) -> None:
    source.mkdir()
    (source / "empty").write_bytes(b"")
    for n in (1, 511, 512, 513, 10000):
        (source / f"f{n}").write_bytes(b"a" * n)
    nested = source / "d1" / "d2" / "d3"
    nested.mkdir(parents=True)
    (nested / "deep.txt").write_bytes(b"b" * 700)
    (source / "emptydir").mkdir()

    prefix_len = len(str(source).lstrip("/")) + 1
    # member path well over 100 chars
    (source / ("L" * max(1, 120 - prefix_len))).write_bytes(b"c" * 100)
    (source / ("long_" + "x" * 150)).write_bytes(b"c" * 10)
    longdir = source / ("D" * 120)
    longdir.mkdir()
    (longdir / "inner.txt").write_bytes(b"d" * 5)
    # boundary names: member path of exactly 99/100/101 chars
    for target_len in (99, 100, 101):
        pad = target_len - prefix_len
        if pad > 0:
            (source / ("b" * pad)).write_bytes(b"e")
            dname = "c" * (pad - 1) if pad > 1 else ""
            if dname:
                (source / dname).mkdir(exist_ok=True)

    # long symlink target (> 100 chars), dangling is fine
    os.symlink("t/" * 60 + "target", source / "longlink")
    os.symlink("short_target", source / "shortlink")
    # symlink to a directory (not followed)
    os.symlink(source / "d1", source / "dirlink")
    # hard link pair, one with a long name
    (source / "hard_a").write_bytes(b"h" * 3000)
    os.link(source / "hard_a", source / "hard_b")
    os.link(source / "hard_a", source / ("hard_" + "z" * 130))


@pytest.mark.skipif(shutil.which("tar") is None, reason="tar not available")
def test_estimate_tar_bytes_matches_tar(tmp_path):
    source = (tmp_path / "src_tree").resolve()
    _build_tree(source)
    actual = _real_tar_size(source, tmp_path / "out.tar")
    est = estimate_tar_bytes(source)
    assert est >= actual
    assert est - actual <= 10240


@pytest.mark.skipif(shutil.which("tar") is None, reason="tar not available")
def test_estimate_tar_bytes_empty_dir(tmp_path):
    source = (tmp_path / "empty_src").resolve()
    source.mkdir()
    actual = _real_tar_size(source, tmp_path / "out.tar")
    est = estimate_tar_bytes(source)
    assert est >= actual
    assert est - actual <= 10240
    assert est % 10240 == 0


@pytest.mark.skipif(shutil.which("tar") is None, reason="tar not available")
def test_estimate_tar_bytes_large_file(tmp_path):
    source = (tmp_path / "big_src").resolve()
    source.mkdir()
    (source / "big.bin").write_bytes(os.urandom(100_000))
    actual = _real_tar_size(source, tmp_path / "out.tar")
    est = estimate_tar_bytes(source)
    assert est >= actual
    assert est - actual <= 10240


def test_estimate_tar_bytes_model(tmp_path):
    source = tmp_path / "m"
    source.mkdir()
    (source / "a").write_bytes(b"x" * 513)
    # entries: dir header + file header + 1024 data + 1024 EOF = 3072 -> 10240
    assert estimate_tar_bytes(source) == 10240


def test_estimate_tar_bytes_missing_source(tmp_path):
    with pytest.raises(StagingError, match="Cannot access"):
        estimate_tar_bytes(tmp_path / "missing")


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can read anything"
)
def test_estimate_tar_bytes_unreadable_dir(tmp_path):
    source = tmp_path / "s"
    locked = source / "locked"
    locked.mkdir(parents=True)
    locked.chmod(0)
    try:
        with pytest.raises(StagingError, match="locked"):
            estimate_tar_bytes(source)
    finally:
        locked.chmod(0o755)


# --------------------------------------------------------------------------
# deposit_required_bytes / retrieve_required_bytes
# --------------------------------------------------------------------------


def test_deposit_required_no_split():
    tar = 10 * GIB
    assert deposit_required_bytes(tar, 500 * GIB) == tar + GIB


def test_deposit_required_split_doubles():
    tar = 600 * GIB
    margin = -(-tar // 100)
    assert deposit_required_bytes(tar, 500 * GIB) == 2 * tar + margin


def test_deposit_required_equal_to_split_not_doubled():
    tar = 500 * GIB
    assert deposit_required_bytes(tar, 500 * GIB) == tar + 5 * GIB


def test_deposit_required_small_margin_is_one_gib():
    assert deposit_required_bytes(1000, 10_000) == 1000 + GIB


@pytest.mark.parametrize("bad", [0, -1])
def test_deposit_required_invalid_split(bad):
    with pytest.raises(StagingError, match="positive"):
        deposit_required_bytes(10, bad)


def test_retrieve_required_plain():
    objs = [("/c/a.tar", 100, "u", "d"), ("/c/a.tar.filelist", 50, "u", "d")]
    assert retrieve_required_bytes(objs, unsplit=False) == 150 + GIB
    assert retrieve_required_bytes(objs, unsplit=True) == 150 + GIB


def test_retrieve_required_unsplit_groups():
    objs = [
        ("/c/a.tar_0000", 10, "u", "d"),
        ("/c/a.tar_0001", 20, "u", "d"),
        ("/c/b.tar_0000", 5, "u", "d"),
        ("/c/b.tar_0000.md5", 1, "u", "d"),
        ("/c/b.tar_0000.filelist", 2, "u", "d"),
        ("/c/x.txt", 7, "u", "d"),
        ("/c/c.tar_12", 3, "u", "d"),
    ]
    total = 10 + 20 + 5 + 1 + 2 + 7 + 3
    assert retrieve_required_bytes(objs, unsplit=False) == total + GIB
    assert retrieve_required_bytes(objs, unsplit=True) == total + 35 + GIB


def test_retrieve_required_large_margin():
    size = 500 * GIB
    objs = [("/c/a.tar_0000", size), ("/c/a.tar_0001", size)]
    total = 2 * size
    margin = -(-total // 100)
    assert retrieve_required_bytes(iter(objs), unsplit=True) == 2 * total + margin


def test_retrieve_required_empty():
    assert retrieve_required_bytes([], unsplit=True) == GIB


# --------------------------------------------------------------------------
# assert_free_space
# --------------------------------------------------------------------------


def test_assert_free_space_insufficient(tmp_path, monkeypatch):
    monkeypatch.setattr(
        staging.shutil, "disk_usage", lambda p: DiskUsage(100, 99, 1024)
    )
    with pytest.raises(StagingError) as excinfo:
        assert_free_space(tmp_path, 2 * GIB, "deposit staging")
    msg = str(excinfo.value)
    assert "deposit staging" in msg
    assert str(tmp_path) in msg
    assert "2.00 GB" in msg
    assert "1.00 KB" in msg
    assert "--staging-dir" in msg
    assert "quota" in msg


def test_assert_free_space_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(
        staging.shutil, "disk_usage", lambda p: DiskUsage(10 * GIB, 0, 10 * GIB)
    )
    assert_free_space(tmp_path, 2 * GIB, "retrieve")


def test_assert_free_space_real(tmp_path):
    assert_free_space(tmp_path, 1, "deposit staging")


def test_estimate_staging_bytes_filelist_matches_tar_verbose(tmp_path):
    src = (tmp_path / "src").resolve()
    (src / "sub" / ("d" * 60)).mkdir(parents=True)
    (src / "a.txt").write_text("a")
    (src / "sub" / "b.bin").write_bytes(b"x" * 600)
    (src / "sub" / ("d" * 60) / ("f" * 70)).write_text("long")
    os.link(src / "a.txt", src / "sub" / "hard")
    os.symlink("a.txt", src / "link")
    out = tmp_path / "out.tar"
    proc = subprocess.run(
        ["tar", "cvf", str(out), str(src)],
        check=True,
        capture_output=True,
    )
    tar_bytes, filelist_bytes = staging.estimate_staging_bytes(src)
    assert tar_bytes == staging.estimate_tar_bytes(src)
    assert tar_bytes >= out.stat().st_size
    assert filelist_bytes == len(proc.stdout)


def test_deposit_required_bytes_includes_filelist():
    base = staging.deposit_required_bytes(10 * staging.GIB, 100 * staging.GIB)
    with_list = staging.deposit_required_bytes(
        10 * staging.GIB, 100 * staging.GIB, 5 * staging.GIB
    )
    assert with_list - base == 5 * staging.GIB


def test_reclaimable_bytes_only_for_marked_root(tmp_path):
    unmarked = tmp_path / "CCBR-1"
    (unmarked / "Analysis").mkdir(parents=True)
    (unmarked / "Analysis" / "x").write_bytes(b"x" * 8192)
    assert staging.reclaimable_bytes(unmarked) == 0
    assert staging.reclaimable_bytes(tmp_path / "missing") == 0

    marked = tmp_path / "CCBR-2"
    staging.prepare_staging_root(marked, "Analysis", {})
    (marked / "Analysis" / "x").write_bytes(b"x" * 8192)
    assert staging.reclaimable_bytes(marked) >= 8192


def test_assert_free_space_counts_reclaimable(monkeypatch, tmp_path):
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(staging.shutil, "disk_usage", lambda _p: usage(100, 90, 10))
    staging.assert_free_space(tmp_path, 25, "deposit staging", reclaimable=20)
    with pytest.raises(staging.StagingError, match="previous staging folder"):
        staging.assert_free_space(tmp_path, 40, "deposit staging", reclaimable=20)


def test_assert_not_deposit_staging(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    staging.assert_not_deposit_staging(plain)
    staging.assert_not_deposit_staging(tmp_path / "missing")
    marked = tmp_path / "CCBR-3"
    staging.prepare_staging_root(marked, "Analysis", {})
    with pytest.raises(staging.StagingError, match="deposit staging folder"):
        staging.assert_not_deposit_staging(marked)


def test_assert_not_deposit_staging_checks_parents_and_symlinks(tmp_path):
    root = tmp_path / "CCBR-4"
    staging.prepare_staging_root(root, "Analysis", {})
    with pytest.raises(staging.StagingError, match="deposit staging folder"):
        staging.assert_not_deposit_staging(root / "Analysis")
    with pytest.raises(staging.StagingError, match="deposit staging folder"):
        staging.assert_not_deposit_staging(root / "Analysis" / "not_yet_created")
    link = tmp_path / "link_into_root"
    link.symlink_to(root / "Analysis")
    with pytest.raises(staging.StagingError, match="deposit staging folder"):
        staging.assert_not_deposit_staging(link)
