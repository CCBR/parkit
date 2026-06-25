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
            print("dm_query_dataobject returned non-zero; no objects found or query failed.")
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
            for entry in (item.get("metadataEntries") or {}).get("selfMetadataEntries", []):
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


def render_ls_tree(collection_path, objects):
    """Print *objects* as a box-drawing tree grouped by immediate parent path."""
    sub_collections: dict[str, list[tuple[str, int | None, str | None, str | None]]] = {}
    for abs_path, size, depositor, deposit_date in objects:
        parent = str(Path(abs_path).parent)
        sub_collections.setdefault(parent, []).append((abs_path, size, depositor, deposit_date))

    def _sub_size(items):
        total = 0
        for _, s, _d, _dt in items:
            if s is None:
                return None
            total += s
        return total

    collection_name = Path(collection_path).name
    total_all = sum(s for _, s, _d, _dt in objects if s is not None) if objects else 0
    print(f"{collection_name}  ({human_size(total_all)})")

    sorted_subs = sorted(sub_collections.keys())
    for sub_idx, sub_path in enumerate(sorted_subs):
        is_last_sub = sub_idx == len(sorted_subs) - 1
        sub_connector = "└──" if is_last_sub else "├──"
        sub_name = Path(sub_path).name
        sub_sz = _sub_size(sub_collections[sub_path])
        sub_sz_str = f"  ({human_size(sub_sz)})" if sub_sz is not None else ""
        print(f"{sub_connector} {sub_name}/{sub_sz_str}")

        child_prefix = "    " if is_last_sub else "│   "
        items = sorted(sub_collections[sub_path], key=lambda x: Path(x[0]).name)
        for item_idx, (abs_path, size, depositor, deposit_date) in enumerate(items):
            is_last_item = item_idx == len(items) - 1
            item_connector = "└──" if is_last_item else "├──"
            fname = Path(abs_path).name
            sz_str = human_size(size) if size is not None else "unknown"
            dep_col = ",".join(filter(None, [depositor, deposit_date])) or ""
            print(f"{child_prefix}{item_connector} {fname:<50}  {sz_str:<12}  {dep_col}")


def render_ls_json(objects):
    """Print *objects* as a JSON array to stdout."""
    records = []
    for abs_path, size, depositor, deposit_date in objects:
        records.append({
            "path": abs_path,
            "size_bytes": size,
            "size_human": human_size(size) if size is not None else None,
            "depositor": depositor,
            "deposit_date": deposit_date,
        })
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
