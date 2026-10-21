"""Staging-area helpers for ``projark deposit`` and ``projark retrieve``.

``projark deposit`` builds a tarball, its filelist, optional split parts and md5
files in a staging folder ``<base>/CCBR-<projectnumber>/<datatype>/``. This module
resolves the staging base (``--staging-dir`` > ``$PROJARK_STAGING_DIR`` >
``/scratch/$USER``), guards against overlapping the source folder, only ever
deletes staging folders that carry the ``.projark_staging`` marker, and checks
free space before any work starts.

Example usage::

    from pathlib import Path
    from parkit.src import staging

    source = Path("/data/CCBR/projects/CCBR-1234").resolve()
    base, is_default = staging.resolve_staging_base("")
    root = staging.staging_root(base, "CCBR-1234")
    staging.assert_no_overlap(root, source)
    staging.check_existing_root(root)
    tar_bytes, filelist_bytes = staging.estimate_staging_bytes(source)
    required = staging.deposit_required_bytes(
        tar_bytes, 500 * staging.GIB, filelist_bytes
    )
    staging.assert_free_space(
        base, required, "deposit staging", staging.reclaimable_bytes(root)
    )
    datatype_dir = staging.prepare_staging_root(
        root, "Analysis", {"projectnumber": "1234", "datatype": "Analysis"}
    )
    # ... create tar / split / md5 in datatype_dir and transfer ...
    staging.remove_staging_root(root)

All failures raise :class:`StagingError`.
"""

import json
import os
import re
import shutil
import stat
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from parkit.src.utils import human_size

MARKER_NAME = ".projark_staging"
ENV_VAR = "PROJARK_STAGING_DIR"
DEFAULT_PARENT = Path("/scratch")
GIB = 1024**3

_TAR_BLOCK = 512
_TAR_RECORD = 10240
_TAR_NAME_FIELD = 100
_SPLIT_PART_RE = re.compile(r"^(.*\.tar)_\d{4}$")


class StagingError(RuntimeError):
    """Raised when the staging area cannot be used safely."""


def _blocks(nbytes: int) -> int:
    """Return *nbytes* rounded up to a whole number of 512-byte tar blocks."""
    return -(-nbytes // _TAR_BLOCK) * _TAR_BLOCK


def _margin(total: int) -> int:
    """Return the safety margin for *total* bytes: max(1 GiB, 1% of total)."""
    return max(GIB, -(-total // 100))


def resolve_staging_base(cli_value: str = "") -> tuple[Path, bool]:
    """Resolve the staging base folder.

    Precedence: *cli_value* (``--staging-dir``) > ``$PROJARK_STAGING_DIR`` >
    ``/scratch/$USER``. The default base is created if missing; a custom base
    must already exist and be a directory.

    Args:
        cli_value: Value of ``--staging-dir`` (empty string when not given).

    Returns:
        Tuple ``(base, is_default)`` where *base* is absolute and resolved.

    Raises:
        StagingError: If ``$USER`` is unset for the default, the custom folder
            does not exist or is not a directory, the base is ``/``, or the base
            is not writable and searchable.
    """
    cli_value = (cli_value or "").strip()
    env_value = os.environ.get(ENV_VAR, "").strip()
    is_default = False
    if cli_value:
        raw, origin = cli_value, "--staging-dir"
    elif env_value:
        raw, origin = env_value, f"${ENV_VAR}"
    else:
        user = os.environ.get("USER", "").strip()
        if not user:
            raise StagingError(
                "USER environment variable is not set; cannot determine the "
                f"default staging folder {DEFAULT_PARENT}/$USER. Set $USER or "
                f"use --staging-dir / ${ENV_VAR}."
            )
        raw, origin, is_default = str(DEFAULT_PARENT / user), "default", True

    base = Path(raw).expanduser().resolve()
    if base == Path(base.anchor):
        raise StagingError(
            f"Staging folder ({origin}) must not be the filesystem root: {base}"
        )
    if is_default:
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StagingError(
                f"Could not create default staging folder {base}: {exc}"
            ) from exc
    elif not base.exists():
        raise StagingError(
            f"Staging folder ({origin}) does not exist: {base}. "
            "Create it first or choose another --staging-dir."
        )
    if not base.is_dir():
        raise StagingError(f"Staging folder ({origin}) is not a directory: {base}")
    if not os.access(base, os.W_OK | os.X_OK):
        raise StagingError(
            f"Staging folder ({origin}) is not writable/searchable: {base}"
        )
    return base, is_default


def staging_root(base: Path, project_tag: str) -> Path:
    """Return the per-project staging root ``base / project_tag``.

    Args:
        base: Staging base folder.
        project_tag: Project tag such as ``CCBR-1234``.

    Returns:
        The staging root path (not created).
    """
    return Path(base) / project_tag


def assert_no_overlap(root: Path, source: Path) -> None:
    """Abort if the staging root and the source folder overlap.

    Both paths are resolved (symlinks followed); *root* may not exist yet.

    Args:
        root: Staging root (``<base>/CCBR-<n>``).
        source: Folder being archived.

    Raises:
        StagingError: If the paths are equal or one is inside the other.
    """
    root_r = Path(root).expanduser().resolve(strict=False)
    source_r = Path(source).expanduser().resolve(strict=False)
    if root_r == source_r:
        raise StagingError(
            f"Staging root {root_r} is the same folder as the source {source_r}; "
            "the tarball would be written inside the folder being archived and "
            "deleting the staging root would delete the source. "
            "Choose another --staging-dir."
        )
    if root_r.is_relative_to(source_r):
        raise StagingError(
            f"Staging root {root_r} is inside the source folder {source_r}; "
            "the tarball would be written inside the folder being archived. "
            "Choose another --staging-dir."
        )
    if source_r.is_relative_to(root_r):
        raise StagingError(
            f"Source folder {source_r} is inside the staging root {root_r}; "
            "deleting the staging root would delete the source data. "
            "Choose another --staging-dir."
        )


def check_existing_root(root: Path) -> None:
    """Verify an existing staging root was created by ``projark deposit``.

    Args:
        root: Staging root to check.

    Raises:
        StagingError: If *root* is a symlink, exists but is not a directory,
            or exists without the ``.projark_staging`` marker file.
    """
    root = Path(root)
    if root.is_symlink():
        raise StagingError(
            f"Staging root {root} is a symbolic link; refusing to use or delete "
            "it. Remove or rename it, or choose another --staging-dir."
        )
    if root.exists():
        if not root.is_dir():
            raise StagingError(
                f"Staging root {root} exists but is not a directory. "
                "Remove or rename it, or choose another --staging-dir."
            )
        if not (root / MARKER_NAME).is_file():
            raise StagingError(
                f"Staging root {root} already exists but was not created by "
                f"projark deposit (no {MARKER_NAME} marker); refusing to delete "
                "it. Remove or rename it, or choose another --staging-dir."
            )


def prepare_staging_root(root: Path, datatype: str, metadata: dict[str, Any]) -> Path:
    """Create a fresh staging root with a marker and a datatype subfolder.

    An existing marked root is deleted and recreated; an unmarked one aborts.

    Args:
        root: Staging root (``<base>/CCBR-<n>``).
        datatype: Datatype subfolder name (e.g. ``Analysis``).
        metadata: Extra JSON-serializable fields written to the marker.

    Returns:
        The datatype folder ``root / datatype``.

    Raises:
        StagingError: If the existing root is unsafe to delete or creation fails.
    """
    root = Path(root)
    check_existing_root(root)
    try:
        if root.exists():
            shutil.rmtree(root)
        datatype_dir = root / datatype
        datatype_dir.mkdir(parents=True)
        marker = {"created_at": datetime.now().astimezone().isoformat(), **metadata}
        (root / MARKER_NAME).write_text(
            json.dumps(marker, indent=2, default=str) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        raise StagingError(f"Could not prepare staging root {root}: {exc}") from exc
    return datatype_dir


def remove_staging_root(root: Path) -> None:
    """Delete a staging root, but only if it carries the projark marker.

    Args:
        root: Staging root to delete. A missing root is a no-op.

    Raises:
        StagingError: If the root exists without the marker or is not a folder.
    """
    root = Path(root)
    if root.exists() or root.is_symlink():
        check_existing_root(root)
        shutil.rmtree(root)


def _name_bytes(name: str) -> int:
    """Return the byte length of a tar member *name*."""
    return len(name.encode("utf-8", "surrogateescape"))


def _long_name_bytes(name: str) -> int:
    """Return extra bytes for a GNU ``././@LongLink`` record if *name* is long."""
    length = _name_bytes(name)
    extra = 0
    if length > _TAR_NAME_FIELD:
        extra = _TAR_BLOCK + _blocks(length + 1)
    return extra


def _member_bytes(
    path: str, st: os.stat_result, seen: dict[tuple[int, int], str]
) -> int:
    """Return the archive bytes GNU tar writes for one filesystem entry."""
    name = path.lstrip("/")
    mode = st.st_mode
    size = 0
    if stat.S_ISSOCK(mode):
        # GNU tar ignores sockets ("socket ignored") and writes nothing.
        size = 0
    elif stat.S_ISDIR(mode):
        size = _TAR_BLOCK + _long_name_bytes(name + "/")
    else:
        key = (st.st_dev, st.st_ino)
        if st.st_nlink > 1 and key in seen:
            size = _TAR_BLOCK + _long_name_bytes(name) + _long_name_bytes(seen[key])
        else:
            if st.st_nlink > 1:
                seen[key] = name
            size = _TAR_BLOCK + _long_name_bytes(name)
            if stat.S_ISREG(mode):
                size += _blocks(st.st_size)
            elif stat.S_ISLNK(mode):
                try:
                    target = os.readlink(path)
                except OSError as exc:
                    raise StagingError(
                        f"Cannot read symlink {path} while estimating tar size: {exc}"
                    ) from exc
                size += _long_name_bytes(target)
    return size


def _listing_bytes(path: str, st: os.stat_result) -> int:
    """Return the bytes ``tar -v`` writes to the filelist for one entry.

    Unlike member names in the archive, ``tar -v`` prints paths as given,
    keeping the leading ``/``.
    """
    name = path
    size = 0
    if not stat.S_ISSOCK(st.st_mode):
        if stat.S_ISDIR(st.st_mode):
            name += "/"
        size = _name_bytes(name) + 1
    return size


def estimate_staging_bytes(source: Path) -> tuple[int, int]:
    """Estimate the tarball and filelist sizes of ``tar cvf OUT <source>``.

    The tarball estimate models GNU tar's gnu format: 512-byte headers, data
    padded to 512 bytes, GNU long-name/long-link records for names > 100 bytes,
    hard links stored once, symlinks not followed, and the end-of-archive
    blocks rounded up to the 10240-byte record size. Sparse files are counted at
    their apparent size. The filelist estimate is one line (member name plus a
    newline) per archived entry, which ``createtar`` writes to ``.filelist``.

    Args:
        source: Absolute folder (or file) that will be archived.

    Returns:
        ``(tar_bytes, filelist_bytes)``.

    Raises:
        StagingError: If *source* or any folder below it cannot be read.
    """
    top = os.path.abspath(os.fspath(source))
    seen: dict[tuple[int, int], str] = {}
    try:
        top_stat = os.lstat(top)
    except OSError as exc:
        raise StagingError(f"Cannot access source {top}: {exc}") from exc
    total = _member_bytes(top, top_stat, seen)
    listing = _listing_bytes(top, top_stat)
    stack = [top] if stat.S_ISDIR(top_stat.st_mode) else []
    while stack:
        current = stack.pop()
        subdirs = []
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    st = entry.stat(follow_symlinks=False)
                    total += _member_bytes(entry.path, st, seen)
                    listing += _listing_bytes(entry.path, st)
                    if stat.S_ISDIR(st.st_mode):
                        subdirs.append(entry.path)
        except OSError as exc:
            raise StagingError(
                f"Cannot read {current} while estimating tar size "
                f"(tar would fail too): {exc}"
            ) from exc
        stack.extend(reversed(subdirs))
    total += 2 * _TAR_BLOCK
    return -(-total // _TAR_RECORD) * _TAR_RECORD, listing


def estimate_tar_bytes(source: Path) -> int:
    """Estimate the size of ``tar cf OUT <source>`` (GNU tar, gnu format).

    See :func:`estimate_staging_bytes`, which also estimates the filelist.

    Args:
        source: Absolute folder (or file) that will be archived.

    Returns:
        Estimated archive size in bytes.

    Raises:
        StagingError: If *source* or any folder below it cannot be read.
    """
    return estimate_staging_bytes(source)[0]


def deposit_required_bytes(
    tar_bytes: int, split_size_bytes: int, filelist_bytes: int = 0
) -> int:
    """Return the peak staging space needed for a deposit.

    Splitting writes the parts while the full tar still exists (about 2x).
    The filelist exists for the whole run and is added explicitly; a margin of
    ``max(1 GiB, 1% of tar)`` covers md5 files and filesystem overhead.

    Args:
        tar_bytes: Estimated tarball size in bytes.
        split_size_bytes: Split threshold/part size in bytes (must be > 0).
        filelist_bytes: Estimated ``.filelist`` size in bytes.

    Returns:
        Required free bytes.

    Raises:
        StagingError: If *split_size_bytes* is not positive.
    """
    if split_size_bytes <= 0:
        raise StagingError(f"Split size must be positive, got {split_size_bytes}")
    peak = tar_bytes * (2 if tar_bytes > split_size_bytes else 1)
    return peak + filelist_bytes + _margin(tar_bytes)


def retrieve_required_bytes(objects: Iterable[tuple], unsplit: bool) -> int:
    """Return the peak local space needed to download *objects*.

    With *unsplit*, every ``*.tar_NNNN`` group is counted twice because the
    merged tar is written while the parts still exist.

    Args:
        objects: Tuples whose first two items are ``(path, size_bytes)``.
        unsplit: Whether split parts will be merged after download.

    Returns:
        Required free bytes including a ``max(1 GiB, 1%)`` margin.
    """
    total = 0
    groups: dict[str, int] = {}
    for obj in objects:
        path, size = str(obj[0]), int(obj[1] or 0)
        total += size
        match = _SPLIT_PART_RE.match(os.path.basename(path))
        if match:
            key = os.path.join(os.path.dirname(path), match.group(1))
            groups[key] = groups.get(key, 0) + size
    extra = sum(groups.values()) if unsplit else 0
    return total + extra + _margin(total)


def reclaimable_bytes(root: Path) -> int:
    """Return the disk space a marked staging root occupies.

    A marked root from a previous deposit is deleted before staging starts, so
    its space is available to the new run. Unmarked roots, symlinks and missing
    roots count as 0 (they are never deleted).

    Args:
        root: Staging root (``<base>/CCBR-<n>``).

    Returns:
        Allocated bytes of all entries below *root* (0 if not reclaimable).

    Raises:
        StagingError: If the marked root cannot be read.
    """
    root = Path(root)
    total = 0
    if root.is_dir() and not root.is_symlink() and (root / MARKER_NAME).is_file():
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                for name in dirnames + filenames:
                    total += os.lstat(os.path.join(dirpath, name)).st_blocks * 512
        except OSError as exc:
            raise StagingError(f"Cannot measure staging root {root}: {exc}") from exc
    return total


def assert_not_deposit_staging(folder: Path) -> None:
    """Abort if *folder* is inside (or is) a deposit staging root.

    ``projark deposit`` deletes the whole marked staging root, so data retrieved
    into it or any folder below it would be lost on the next deposit of that
    project. *folder* is resolved first so symlinked paths are caught.

    Args:
        folder: Local base folder a retrieve would download into.

    Raises:
        StagingError: If *folder* or any parent contains the ``.projark_staging``
            marker.
    """
    folder = Path(folder).resolve()
    marked = next(
        (p for p in (folder, *folder.parents) if (p / MARKER_NAME).is_file()), None
    )
    if marked is not None:
        raise StagingError(
            f"{folder} is inside the projark deposit staging folder {marked} (it "
            f"contains {MARKER_NAME}); a later deposit of that project would delete "
            "it, including retrieved data. Remove the leftover staging folder or "
            "choose another --folder/--staging-dir."
        )


def assert_free_space(
    path: Path, required: int, purpose: str, reclaimable: int = 0
) -> None:
    """Abort if the filesystem holding *path* has less than *required* free.

    Args:
        path: Existing folder on the target filesystem.
        required: Required free bytes.
        purpose: Short description used in the error (e.g. ``deposit staging``).
        reclaimable: Bytes that will be freed before work starts (e.g. a
            previous marked staging root that is deleted first).

    Raises:
        StagingError: If free space is insufficient or cannot be determined.
    """
    try:
        free = shutil.disk_usage(path).free
    except OSError as exc:
        raise StagingError(f"Cannot determine free space for {path}: {exc}") from exc
    available = free + max(reclaimable, 0)
    if available < required:
        reclaim_note = ""
        if reclaimable > 0:
            reclaim_note = (
                f" (plus {human_size(reclaimable)} from the previous staging "
                "folder that will be deleted)"
            )
        raise StagingError(
            f"Not enough free space for {purpose} in {path}: need about "
            f"{human_size(required)} ({required} bytes), only {human_size(free)} "
            f"({free} bytes) free{reclaim_note}. Choose another "
            "--staging-dir/--folder or free up space. Note: per-user/group quotas "
            "are not visible to this check."
        )


__all__ = [
    "DEFAULT_PARENT",
    "ENV_VAR",
    "GIB",
    "MARKER_NAME",
    "StagingError",
    "assert_free_space",
    "assert_no_overlap",
    "assert_not_deposit_staging",
    "check_existing_root",
    "deposit_required_bytes",
    "estimate_staging_bytes",
    "estimate_tar_bytes",
    "prepare_staging_root",
    "reclaimable_bytes",
    "remove_staging_root",
    "resolve_staging_base",
    "retrieve_required_bytes",
    "staging_root",
]
