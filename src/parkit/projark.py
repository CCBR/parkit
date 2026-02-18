import argparse
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from parkit.src.VersionCheck import __version__
from parkit.src.checkapisync import check_hpc_dme_apis_sync
from parkit.src.createtar import createtar
from parkit.src.utils import get_md5sum, run_dm_cmd


DEFAULT_SPLIT_SIZE_GB = 500.0


def _human_size(num_bytes):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    return f"{value:.2f} {units[unit_index]}"


def _info(message):
    print(f"[projark] ℹ️  {message}")


def _step(step_number, message):
    print(f"[projark] 🚀 Step {step_number}: {message}")


def _ok(message):
    print(f"[projark] ✅ {message}")


def _error(message):
    print(f"[projark] ❌ ERROR: {message}")
    return 1


def _normalize_project_number(raw_value):
    value = raw_value.strip()
    match = re.fullmatch(r"(?i)(?:ccbr[-_]?)?(\d+)", value)
    if not match:
        raise argparse.ArgumentTypeError(
            "Invalid --projectnumber. Accepts values like 1234, ccbr1234, CCBR-1234, ccbr_1234."
        )
    return match.group(1)


def _normalize_datatype(raw_value):
    value = raw_value.strip().lower()
    if value not in {"analysis", "rawdata"}:
        raise argparse.ArgumentTypeError(
            "Invalid --datatype. Must be Analysis or Rawdata."
        )
    return value.title()


def _project_tag(project_number):
    return f"CCBR-{project_number}"


def _project_collection_path(project_number):
    return f"/CCBR_Archive/GRIDFTP/Project_CCBR-{project_number}"


def _default_tarname(project_number):
    return f"ccbr{project_number}.tar"


def _run_sync_gate():
    _step(1, "checking HPC_DME_APIs sync status via parkit checkapisync ...")
    rc = check_hpc_dme_apis_sync()
    if rc != 0:
        _info("Repository is not in sync. Please run 'parkit syncapi' first, then retry projark.")
        return False
    _ok("Sync check passed.")
    return True


def _require_helix():
    host = os.environ.get("HOSTNAME", "")
    fqdn = socket.getfqdn()
    candidates = {host, fqdn}
    if "helix.nih.gov" not in candidates:
        raise RuntimeError(
            f"This command only runs on helix.nih.gov. Observed HOSTNAME='{host}', FQDN='{fqdn}'."
        )


def _require_terminal_multiplexer():
    # Long-running deposits should run in a resilient terminal session.
    # TMUX is set inside tmux; STY is set inside GNU screen.
    in_tmux = bool(os.environ.get("TMUX"))
    in_screen = bool(os.environ.get("STY"))
    if not (in_tmux or in_screen):
        raise RuntimeError(
            "projark deposit must be run inside tmux or screen because transfers may take a long time. "
            "Please start a tmux/screen session and rerun."
        )


def _collection_exists(collection_path):
    cmd = f"dm_get_collection {shlex.quote(collection_path)}"
    proc = run_dm_cmd(
        dm_cmd=cmd, errormsg=f"Failed while checking collection {collection_path}", returnproc=True, exitiffails=False
    )
    return proc.returncode == 0


def _dataobject_exists(object_path):
    cmd = f"dm_get_dataobject {shlex.quote(object_path)}"
    proc = run_dm_cmd(
        dm_cmd=cmd, errormsg=f"Failed while checking object {object_path}", returnproc=True, exitiffails=False
    )
    return proc.returncode == 0


def _register_collection(collection_path, collection_type):
    # Minimal metadata payload used to create a collection if it does not exist.
    payload = {"metadataEntries": [{"attribute": "collection_type", "value": collection_type}]}
    with NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(payload, tmp, indent=2)
        temp_json = tmp.name

    try:
        cmd = f"dm_register_collection {shlex.quote(temp_json)} {shlex.quote(collection_path)}"
        run_dm_cmd(dm_cmd=cmd, errormsg=f"Failed to create collection {collection_path}")
    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)


def _ensure_deposit_collections(base_collection, datatype):
    datatype_collection = f"{base_collection}/{datatype}"
    _info(f"Step 3: verifying destination collection: {datatype_collection}")
    if _collection_exists(datatype_collection):
        _info("Destination datatype collection already exists.")
        return datatype_collection

    _info(f"Datatype collection missing: {datatype_collection}")
    if not _collection_exists(base_collection):
        _info(f"Project collection missing: {base_collection}")
        _info("Creating project collection first ...")
        _register_collection(base_collection, "Project")
    else:
        _info("Project collection exists.")

    _info(f"Creating datatype collection: {datatype_collection}")
    _register_collection(datatype_collection, datatype)
    return datatype_collection


def _prepare_scratch_dirs(project_tag, datatype):
    user = os.environ.get("USER", "")
    if not user:
        raise RuntimeError("USER environment variable is not set.")

    scratch_root = Path("/scratch") / user / project_tag
    datatype_dir = scratch_root / datatype

    _info(f"Step 4: preparing scratch staging area at {scratch_root}")
    if scratch_root.exists():
        _info("Scratch project directory exists; deleting and recreating it.")
        shutil.rmtree(scratch_root)

    datatype_dir.mkdir(parents=True, exist_ok=True)
    _info(f"Created datatype staging directory: {datatype_dir}")
    return scratch_root, datatype_dir


def _split_if_needed(tar_path, split_size_gb):
    tar_size = tar_path.stat().st_size
    _info(f"Tar size is {_human_size(tar_size)} ({tar_size} bytes).")
    split_size_bytes = int(split_size_gb * 1024 * 1024 * 1024)
    if split_size_bytes <= 0:
        raise RuntimeError("--split-size-gb must be greater than 0.")

    if tar_size <= split_size_bytes:
        _info(f"Tar size is <= {split_size_gb:g}GB; split not needed.")
        return [tar_path]

    _info(f"Tar size is > {split_size_gb:g}GB; splitting into {split_size_gb:g}GB chunks ...")
    split_prefix = str(tar_path) + "_"
    cmd = [
        "split",
        "-b",
        str(split_size_bytes),
        "-d",
        "-a",
        "4",
        "--numeric-suffixes=1",
        str(tar_path),
        split_prefix,
    ]
    subprocess.run(cmd, check=True)
    tar_path.unlink()

    parts = sorted(tar_path.parent.glob(f"{tar_path.name}_????"))
    if not parts:
        raise RuntimeError("split command completed but no chunk files were produced.")

    _info(f"Created {len(parts)} chunk file(s).")
    return parts


def _write_md5_files(directory):
    _info("Generating md5 files for staged payload files ...")
    for file_path in sorted(directory.iterdir()):
        if not file_path.is_file() or file_path.name.endswith(".md5"):
            continue
        checksum = get_md5sum(str(file_path))
        md5_path = file_path.with_name(f"{file_path.name}.md5")
        with open(md5_path, "w") as handle:
            handle.write(f"{checksum}\n")
        _info(f"md5 written: {md5_path.name}")


def _run_deposit(args):
    if not _run_sync_gate():
        return 1

    _step(2, "verifying execution host ...")
    _require_helix()
    _ok("Host check passed (helix.nih.gov).")
    _info("Checking for tmux/screen session for long-running deposit ...")
    _require_terminal_multiplexer()
    _ok("Session check passed (inside tmux/screen).")

    project_tag = _project_tag(args.projectnumber)
    base_collection = _project_collection_path(args.projectnumber)
    datatype = args.datatype
    datatype_collection = _ensure_deposit_collections(base_collection, datatype)

    scratch_root, datatype_dir = _prepare_scratch_dirs(project_tag, datatype)

    tarname = args.tarname if args.tarname else _default_tarname(args.projectnumber)
    if "/" in tarname:
        return _error("--tarname must be a file name, not a path.")
    tar_path = datatype_dir / tarname

    _step(5, f"creating tarball from folder: {args.folder}")
    _info(f"Tar output path: {tar_path}")
    createtar(args.folder, str(tar_path))
    _ok(f"Created: {tar_path}")
    _ok(f"Created: {tar_path}.filelist")

    _split_if_needed(tar_path, args.split_size_gb)
    _write_md5_files(datatype_dir)

    _step(6, "transferring staged directory to HPC-DME ...")
    src_dir = f"{datatype_dir}/"
    dst_dir = f"{datatype_collection}/"
    cmd = f"dm_register_directory -c -r -t 4 -s {shlex.quote(src_dir)} {shlex.quote(dst_dir)}"
    run_dm_cmd(dm_cmd=cmd, errormsg="dm_register_directory failed during deposit.")
    _ok("Transfer completed.")

    if args.cleanup:
        _step(7, f"cleanup requested; deleting {scratch_root}")
        shutil.rmtree(scratch_root)
        _ok("Cleanup completed.")
    else:
        _step(7, f"cleanup not requested; staged files retained at {scratch_root}")

    _ok("Deposit workflow finished successfully.")
    return 0


def _parse_filenames(csv_value):
    filenames = [part.strip() for part in csv_value.split(",") if part.strip()]
    if not filenames:
        raise ValueError("--filenames must contain at least one comma-separated file name.")
    return filenames


def _ensure_retrieve_collections(base_collection, datatype):
    datatype_collection = f"{base_collection}/{datatype}"
    _info(f"Step 3: verifying source collection: {datatype_collection}")
    if _collection_exists(datatype_collection):
        _info("Source datatype collection exists.")
        return datatype_collection

    if not _collection_exists(base_collection):
        raise RuntimeError(
            f"Project collection does not exist: {base_collection}. Cannot retrieve."
        )

    raise RuntimeError(
        f"Datatype collection does not exist: {datatype_collection}. Cannot retrieve."
    )


def _merge_split_tar_parts(target_dir):
    # Merge all groups that match <name>.tar_0001, <name>.tar_0002, ...
    part_groups = {}
    for part in sorted(target_dir.glob("*.tar_????")):
        match = re.match(r"(.+\.tar)_(\d{4})$", part.name)
        if not match:
            continue
        tar_name = match.group(1)
        part_groups.setdefault(tar_name, []).append(part)

    if not part_groups:
        _info("No split tar parts found for merge.")
        return

    for tar_name, parts in part_groups.items():
        parts = sorted(parts, key=lambda p: p.name)
        merged_tar = target_dir / tar_name
        _info(f"Merging {len(parts)} part(s) into {merged_tar}")
        with open(merged_tar, "wb") as out_handle:
            for part in parts:
                with open(part, "rb") as in_handle:
                    shutil.copyfileobj(in_handle, out_handle)
        for part in parts:
            part.unlink()
        _info(f"Merged tar created and part files removed: {merged_tar}")


def _run_retrieve(args):
    if not _run_sync_gate():
        return 1

    _step(2, "verifying execution host ...")
    _require_helix()
    _ok("Host check passed (helix.nih.gov).")
    _info("Checking for tmux/screen session for long-running retrieve ...")
    _require_terminal_multiplexer()
    _ok("Session check passed (inside tmux/screen).")

    base_collection = _project_collection_path(args.projectnumber)
    datatype = args.datatype
    datatype_collection = _ensure_retrieve_collections(base_collection, datatype)

    project_tag = _project_tag(args.projectnumber)
    user = os.environ.get("USER", "")
    if not user:
        return _error("USER environment variable is not set.")

    base_local = Path(args.folder) if args.folder else Path("/scratch") / user / project_tag
    target_dir = base_local / datatype
    target_dir.mkdir(parents=True, exist_ok=True)
    _step(4, f"local download directory: {target_dir}")

    if args.filenames:
        _step(5, "parsing requested filenames ...")
        filenames = _parse_filenames(args.filenames)

        _step(6, "verifying all requested objects exist ...")
        missing = []
        for filename in filenames:
            object_path = f"{datatype_collection}/{filename}"
            exists = _dataobject_exists(object_path)
            _info(f"  - {filename}: {'FOUND' if exists else 'MISSING'}")
            if not exists:
                missing.append(filename)
        if missing:
            return _error(f"Cannot proceed; missing object(s): {', '.join(missing)}")

        _step(7, "downloading requested objects ...")
        for filename in filenames:
            object_path = f"{datatype_collection}/{filename}"
            cmd = f"dm_download_dataobject {shlex.quote(object_path)} {shlex.quote(str(target_dir))}"
            run_dm_cmd(dm_cmd=cmd, errormsg=f"Failed to download {filename}")
            _ok(f"Downloaded: {filename}")
    else:
        _step(5, "no --filenames provided; full collection mode selected.")
        _step(6, "downloading full collection ...")
        # Download the datatype collection under base_local so we get:
        # <base_local>/<datatype>/...
        # and avoid nested paths like <base_local>/<datatype>/<datatype>/...
        cmd = f"dm_download_collection {shlex.quote(datatype_collection)} {shlex.quote(str(base_local))}"
        run_dm_cmd(dm_cmd=cmd, errormsg=f"Failed to download collection {datatype_collection}")
        _ok(f"Downloaded full collection: {datatype_collection}")
        _step(7, "per-file verification skipped in full collection mode.")

    if args.unspilt:
        _step(8, "--unspilt requested; checking for tar parts to merge ...")
        _merge_split_tar_parts(target_dir)
    else:
        _step(8, "--unspilt not requested; skipping merge step.")

    _ok("Retrieve workflow finished successfully.")
    return 0


def _build_parser():
    parser = argparse.ArgumentParser(
        description="projark: project archival helper built on parkit"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"projark is part of parkit; parkit version: {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_deposit = subparsers.add_parser(
        "deposit",
        help="Archive a project folder to /CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>",
    )
    parser_deposit.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"projark is part of parkit; parkit version: {__version__}",
    )
    parser_deposit.add_argument("--folder", required=True, help="Folder to archive")
    parser_deposit.add_argument(
        "--projectnumber",
        "--project-number",
        type=_normalize_project_number,
        required=True,
        help="Project number (e.g. 1234, ccbr1234, CCBR-1234, ccbr_1234)",
    )
    parser_deposit.add_argument(
        "--datatype",
        type=_normalize_datatype,
        default="Analysis",
        help="Analysis or Rawdata (case-insensitive). Default: Analysis",
    )
    parser_deposit.add_argument(
        "--tarname",
        default="",
        help="Optional tar file name override (default: ccbr<projectnumber>.tar)",
    )
    parser_deposit.add_argument(
        "--split-size-gb",
        type=float,
        default=DEFAULT_SPLIT_SIZE_GB,
        help="Tar split threshold/chunk size in GB (default: 500)",
    )
    parser_deposit.add_argument(
        "--cleanup",
        action="store_true",
        default=True,
        help="Delete /scratch/$USER/CCBR-<projectnumber> after successful transfer (default: enabled)",
    )
    parser_deposit.add_argument(
        "--no-cleanup",
        dest="cleanup",
        action="store_false",
        help="Keep /scratch/$USER/CCBR-<projectnumber> after successful transfer",
    )

    parser_retrieve = subparsers.add_parser(
        "retrieve",
        help="Retrieve selected files from /CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>/<datatype>",
    )
    parser_retrieve.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"projark is part of parkit; parkit version: {__version__}",
    )
    parser_retrieve.add_argument(
        "--folder",
        default="",
        help="Local base folder (default: /scratch/$USER/CCBR-<projectnumber>)",
    )
    parser_retrieve.add_argument(
        "--projectnumber",
        "--project-number",
        type=_normalize_project_number,
        required=True,
        help="Project number (e.g. 1234, ccbr1234, CCBR-1234, ccbr_1234)",
    )
    parser_retrieve.add_argument(
        "--datatype",
        type=_normalize_datatype,
        default="Analysis",
        help="Analysis or Rawdata (case-insensitive). Default: Analysis",
    )
    parser_retrieve.add_argument(
        "--filenames",
        required=False,
        default="",
        help="Comma-separated file names to retrieve (omit to download full collection)",
    )
    parser_retrieve.add_argument(
        "--unspilt",
        "--unsplit",
        action="store_true",
        help="Merge split parts (*.tar_0001, *.tar_0002, ...) into a tar after download",
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.command == "deposit":
            return_code = _run_deposit(args)
        elif args.command == "retrieve":
            return_code = _run_retrieve(args)
        else:
            parser.print_help()
            return_code = 1
    except KeyboardInterrupt:
        _info("Interrupted by user.")
        return_code = 130
    except Exception as exc:
        return_code = _error(str(exc))

    sys.exit(return_code)


if __name__ == "__main__":
    main()
