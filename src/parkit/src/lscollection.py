"""lscollection — list HPC-DME collection contents as a tree or JSON.

Public API
----------
ls_collection(collection_path, json_output=False) -> int
    Query all data objects under *collection_path* and render them as a
    tree (default) or as a JSON array (when *json_output* is True).
    Returns 0 on success.

The functions in this module are also used by ``projark ls`` so that
both ``parkit ls`` and ``projark ls`` share a single implementation.
"""

import json
import os
import shlex
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from parkit.src.utils import human_size, run_dm_cmd


_LS_CRITERIA = {
    "compoundQuery": {
        "operator": "AND",
        "queries": [
            {
                "attribute": "source_file_size",
                "value": "0",
                "operator": "NUM_GREATER_OR_EQUAL",
            }
        ],
    },
    "detailedResponse": True,
    "page": 1,
    "totalCount": True,
}


def parse_deposit_date(raw_value):
    """Parse a DME ``data_transfer_completed`` value to ``YYMMDD`` string.

    Accepts ``'MM-DD-YYYY HH:MM:SS'`` or ``'MM-DD-YYYY'``.
    Returns ``None`` if the value is absent or cannot be parsed.
    """
    if not raw_value:
        return None
    for fmt in ("%m-%d-%Y %H:%M:%S", "%m-%d-%Y"):
        try:
            return datetime.strptime(str(raw_value).strip(), fmt).strftime("%y%m%d")
        except ValueError:
            pass
    return None


def query_all_dataobjects(collection_path):
    """Return a list of ``(absolute_path, size_bytes, depositor, deposit_date)``
    for every data object under *collection_path*, iterating all pages.

    *depositor* is ``registered_by_name`` falling back to ``registered_by``,
    or ``None`` if unavailable.
    *deposit_date* is ``data_transfer_completed`` formatted as ``YYMMDD``, or ``None``.
    """
    objects = []
    page = 1
    while True:
        criteria = dict(_LS_CRITERIA)
        criteria["page"] = page
        with NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            json.dump(criteria, tmp, indent=2)
            criteria_file = tmp.name
        try:
            cmd = (
                f"dm_query_dataobject -o /dev/stdout"
                f" {shlex.quote(criteria_file)} {shlex.quote(collection_path)}"
            )
            proc = run_dm_cmd(
                dm_cmd=cmd,
                errormsg="dm_query_dataobject failed during ls",
                returnproc=True,
                exitiffails=False,
            )
        finally:
            if os.path.exists(criteria_file):
                os.remove(criteria_file)

        if proc.returncode != 0:
            print(
                "dm_query_dataobject returned non-zero; no objects found or query failed."
            )
            break

        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, AttributeError):
            print("Could not parse dm_query_dataobject output as JSON.")
            break

        page_items = data.get("dataObjects", []) or []
        for item in page_items:
            abs_path = (item.get("dataObject") or {}).get("absolutePath", "")
            size = None
            depositor_name = None
            depositor_id = None
            deposit_date = None
            for entry in (item.get("metadataEntries") or {}).get(
                "selfMetadataEntries", []
            ):
                attr = entry.get("attribute")
                if attr == "source_file_size":
                    try:
                        size = int(entry["value"])
                    except (ValueError, TypeError):
                        pass
                elif attr == "registered_by_name":
                    depositor_name = str(entry["value"]).strip() or None
                elif attr == "registered_by":
                    depositor_id = str(entry["value"]).strip() or None
                elif attr == "data_transfer_completed":
                    deposit_date = parse_deposit_date(entry["value"])
            depositor = depositor_name or depositor_id
            if abs_path:
                objects.append((abs_path, size, depositor, deposit_date))

        total = data.get("totalCount", 0) or 0
        limit = data.get("limit", 100) or 100
        if page * limit >= total:
            break
        page += 1

    return objects


def _build_tree(collection_path, objects):
    """Build a nested dict tree from *objects* relative to *collection_path*.

    Each node is a dict with:
      '__files__': list of (name, abs_path, size, depositor, deposit_date)
      '<subdir>':  child node (same structure)
    """
    root = {"__files__": []}
    prefix = collection_path.rstrip("/") + "/"
    for abs_path, size, depositor, deposit_date in objects:
        if not abs_path.startswith(prefix):
            continue
        rel = abs_path[len(prefix) :]
        parts = rel.split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {"__files__": []})
        node["__files__"].append((parts[-1], abs_path, size, depositor, deposit_date))
    return root


def _node_size(node):
    """Recursively sum source_file_size for all files under *node*. Returns None if any unknown."""
    total = 0
    for _name, _path, s, _d, _dt in node.get("__files__", []):
        if s is None:
            return None
        total += s
    for key, child in node.items():
        if key == "__files__":
            continue
        cs = _node_size(child)
        if cs is None:
            return None
        total += cs
    return total


def _render_node(node, prefix, is_last, label, indent):
    """Recursively render a tree node."""
    connector = "└──" if is_last else "├──"
    sz = _node_size(node)
    sz_str = f"  ({human_size(sz)})" if sz is not None else ""
    # directory node
    print(f"{indent}{connector} {label}/{sz_str}")
    child_indent = indent + ("    " if is_last else "│   ")

    subdirs = sorted(k for k in node if k != "__files__")
    files = sorted(node.get("__files__", []), key=lambda x: x[0])
    total_children = len(subdirs) + len(files)

    for idx, subdir in enumerate(subdirs):
        is_last_child = idx == total_children - 1
        _render_node(node[subdir], prefix, is_last_child, subdir, child_indent)

    for idx, (fname, _path, size, depositor, deposit_date) in enumerate(files):
        item_idx = len(subdirs) + idx
        is_last_item = item_idx == total_children - 1
        item_connector = "└──" if is_last_item else "├──"
        sz_str = human_size(size) if size is not None else "unknown"
        dep_col = ",".join(filter(None, [depositor, deposit_date])) or ""
        print(f"{child_indent}{item_connector} {fname:<50}  {sz_str:<12}  {dep_col}")


def render_ls_tree(collection_path, objects):
    """Print *objects* as a recursive box-drawing tree rooted at *collection_path*."""
    root = _build_tree(collection_path, objects)
    collection_name = Path(collection_path).name
    total_all = _node_size(root)
    total_str = f"  ({human_size(total_all)})" if total_all is not None else ""
    print(f"{collection_name}{total_str}")

    subdirs = sorted(k for k in root if k != "__files__")
    files = sorted(root.get("__files__", []), key=lambda x: x[0])
    total_top = len(subdirs) + len(files)

    for idx, subdir in enumerate(subdirs):
        is_last = idx == total_top - 1
        _render_node(root[subdir], collection_path, is_last, subdir, "")

    for idx, (fname, _path, size, depositor, deposit_date) in enumerate(files):
        item_idx = len(subdirs) + idx
        is_last = item_idx == total_top - 1
        connector = "└──" if is_last else "├──"
        sz_str = human_size(size) if size is not None else "unknown"
        dep_col = ",".join(filter(None, [depositor, deposit_date])) or ""
        print(f"{connector} {fname:<50}  {sz_str:<12}  {dep_col}")


def render_ls_json(objects):
    """Print *objects* as a JSON array to stdout."""
    records = []
    for abs_path, size, depositor, deposit_date in objects:
        records.append(
            {
                "path": abs_path,
                "size_bytes": size,
                "size_human": human_size(size) if size is not None else None,
                "depositor": depositor,
                "deposit_date": deposit_date,
            }
        )
    print(json.dumps(records, indent=2))


def ls_collection(collection_path, json_output=False):
    """Query all data objects under *collection_path* and render output.

    Parameters
    ----------
    collection_path:
        Full HPC-DME absolute path (e.g. ``/CCBR_Archive/GRIDFTP/Project_CCBR-982``).
    json_output:
        When ``True``, emit a JSON array instead of the tree view.

    Returns
    -------
    int
        0 on success.
    """
    objects = query_all_dataobjects(collection_path)
    if not objects:
        print(f"No data objects found under {collection_path}.")
        return 0

    if json_output:
        render_ls_json(objects)
    else:
        print()
        render_ls_tree(collection_path, objects)
        print()
    return 0
