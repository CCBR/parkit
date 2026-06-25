import argparse
from datetime import datetime
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
NOTIFY_FROM_EMAIL = "NCICCBR@mail.nih.gov"


def _human_size(num_bytes):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    return f"{value:.2f} {units[unit_index]}"


def _info(message):
    print(f"{_log_prefix()} ℹ️  {message}")


def _step(step_number, message):
    print(f"{_log_prefix()} 🚀 Step {step_number}: {message}")


def _ok(message):
    print(f"{_log_prefix()} ✅ {message}")


def _error(message):
    print(f"{_log_prefix()} ❌ ERROR: {message}")
    return 1


def _log_prefix():
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    return f"[projark {timestamp}]"


def _duration_hms(start_time, end_time):
    total_seconds = max(0, int((end_time - start_time).total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _print_hpcdme_properties():
    hpc_dm_utils = os.environ.get("HPC_DM_UTILS", "")
    props_path = Path(hpc_dm_utils) / "hpcdme.properties"
    _info(f"HPC-DME configuration ({props_path}):")
    try:
        with open(props_path) as fh:
            for line in fh:
                stripped = line.rstrip("\n")
                if stripped.startswith("#") or stripped.strip() == "":
                    continue
                print(f"    {stripped}")
    except OSError as e:
        _info(f"Could not read {props_path}: {e}")


_PROXY_KEYS = ("hpc.server.proxy.url", "hpc.server.proxy.port")


def _check_no_proxy_settings():
    """Return True if safe to proceed, False if active proxy lines are found."""
    hpc_dm_utils = os.environ.get("HPC_DM_UTILS", "")
    props_path = Path(hpc_dm_utils) / "hpcdme.properties"
    bad_lines = []
    try:
        with open(props_path) as fh:
            for lineno, line in enumerate(fh, start=1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped == "":
                    continue
                if any(stripped.startswith(key) for key in _PROXY_KEYS):
                    bad_lines.append((lineno, stripped))
    except OSError as e:
        _info(f"Could not read {props_path} for proxy check: {e}")
        return True  # non-fatal; let the transfer attempt proceed
    if bad_lines:
        _error(
            f"Active proxy settings found in {props_path}. "
            "Per HPC-DME team guidance (Udit Sehgal), proxy lines must be "
            "commented out. Please prefix each with '#' and retry."
        )
        for lineno, text in bad_lines:
            print(f"    line {lineno}: {text}")
        return False
    return True


def _resolved_path_for_report(raw_path):
    if not raw_path:
        return ""
    try:
        return str(Path(raw_path).expanduser().resolve())
    except OSError:
        return raw_path


def _send_notification_email(
    args, status, return_code, start_time, end_time, error_message=""
):
    user = os.environ.get("USER", "").strip()
    if not user:
        _info("Email notification skipped: USER environment variable is not set.")
        return

    to_email = f"{user}@nih.gov"
    command = getattr(args, "command", "unknown")
    projectnumber = getattr(args, "projectnumber", "")
    datatype = getattr(args, "datatype", "")
    folder = _resolved_path_for_report(getattr(args, "folder", ""))
    host = socket.getfqdn() or os.environ.get("HOSTNAME", "unknown")
    project_label = _project_tag(projectnumber) if projectnumber else "N/A"
    datatype_label = datatype if datatype else "N/A"
    duration = _duration_hms(start_time, end_time)

    subject = f"[projark] {status} {command} {project_label} ({datatype_label})"
    body_lines = [
        f"Status: {status}",
        f"Command: projark {command}",
        f"Project: {projectnumber or 'N/A'}",
        f"Datatype: {datatype_label}",
        f"User: {user}",
        f"Host: {host}",
        f"Folder: {folder or 'N/A'}",
        f"Start: {start_time.isoformat(timespec='seconds')}",
        f"End: {end_time.isoformat(timespec='seconds')}",
        f"Duration: {duration}",
        f"Return code: {return_code}",
    ]
    if error_message:
        body_lines.append(f"Error: {error_message}")
    body = "\n".join(body_lines) + "\n"

    _info(
        f"Sending completion email to {to_email} from {NOTIFY_FROM_EMAIL} (status: {status}) ..."
    )

    mailx = shutil.which("mailx")
    if mailx:
        proc = subprocess.run(
            [mailx, "-r", NOTIFY_FROM_EMAIL, "-s", subject, to_email],
            input=body,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            _ok("Email notification sent via mailx.")
            return
        err = (proc.stderr or proc.stdout or "").strip()
        print(
            f"{_log_prefix()} ❌ Email notification failed via mailx "
            f"(exit {proc.returncode}): {err or 'no error output'}"
        )

    sendmail = shutil.which("sendmail")
    if sendmail:
        message = (
            f"From: {NOTIFY_FROM_EMAIL}\nTo: {to_email}\nSubject: {subject}\n\n{body}"
        )
        proc = subprocess.run(
            [sendmail, "-f", NOTIFY_FROM_EMAIL, "-t"],
            input=message,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            _ok("Email notification sent via sendmail.")
            return
        err = (proc.stderr or proc.stdout or "").strip()
        print(
            f"{_log_prefix()} ❌ Email notification failed via sendmail "
            f"(exit {proc.returncode}): {err or 'no error output'}"
        )

    if not mailx and not sendmail:
        print(
            f"{_log_prefix()} ❌ Email notification failed: neither 'mailx' nor "
            "'sendmail' is available on this host."
        )


def _normalize_project_number(raw_value):
    value = raw_value.strip()
    # Allow repeated leading CCBR prefixes, each optionally followed by '-' or '_'.
    # After stripping those prefixes, accept any non-empty project number.
    normalized = re.sub(r"(?i)^(?:(?:ccbr)(?:[-_]?))+", "", value).strip()
    if not normalized:
        raise argparse.ArgumentTypeError(
            "Invalid --projectnumber. Provide a non-empty value after optional leading "
            "CCBR prefixes (e.g. 1234, abcd, ccbr1234, CCBR-abcd, ccbr_ccbr-1234abc)."
        )
    return normalized


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


def _resolve_existing_directory(raw_path, arg_name="--folder"):
    try:
        resolved = Path(raw_path).expanduser().resolve(strict=True)
    except FileNotFoundError:
        raise RuntimeError(f"{arg_name} path does not exist: {raw_path}")
    except OSError as exc:
        raise RuntimeError(f"Failed to resolve {arg_name} path '{raw_path}': {exc}")
    if not resolved.is_dir():
        raise RuntimeError(f"{arg_name} must point to a directory: {resolved}")
    return resolved


def _resolve_output_directory(raw_path):
    try:
        return Path(raw_path).expanduser().resolve()
    except OSError as exc:
        raise RuntimeError(f"Failed to resolve --folder path '{raw_path}': {exc}")


def _run_sync_gate():
    _step(1, "checking HPC_DME_APIs sync status via parkit checkapisync ...")
    rc = check_hpc_dme_apis_sync()
    if rc != 0:
        _info(
            "Repository is not in sync. Please run 'parkit syncapi' first, then retry projark."
        )
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
    # Open OnDemand desktop shells usually expose one or more OOD variables and
    # a graphical session/display marker.
    ood_env_markers = ("OOD_PORTAL", "OOD_JOBID", "OOD_SESSION_ID", "OOD_HOST")
    has_ood_marker = any(os.environ.get(marker) for marker in ood_env_markers)
    xdg_session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    has_graphical_session = xdg_session_type in {"x11", "wayland"}
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    in_ood_graphical_session = has_ood_marker and (has_graphical_session or has_display)

    if not (in_tmux or in_screen or in_ood_graphical_session):
        raise RuntimeError(
            "projark must be run inside tmux, screen, or an Open OnDemand graphical session "
            "because transfers may take a long time. Please start one of these session types and rerun."
        )


def _collection_exists(collection_path):
    cmd = f"dm_get_collection {shlex.quote(collection_path)}"
    proc = run_dm_cmd(
        dm_cmd=cmd,
        errormsg=f"Failed while checking collection {collection_path}",
        returnproc=True,
        exitiffails=False,
    )
    return proc.returncode == 0


def _dataobject_exists(object_path):
    cmd = f"dm_get_dataobject {shlex.quote(object_path)}"
    proc = run_dm_cmd(
        dm_cmd=cmd,
        errormsg=f"Failed while checking object {object_path}",
        returnproc=True,
        exitiffails=False,
    )
    return proc.returncode == 0


def _insert_counter(name, n):
    """Insert _{n:03d} before the first '.' in name, or append if no '.' exists.

    Examples:
        ccbr1431.tar           -> ccbr1431_001.tar
        ccbr1431.tar.filelist  -> ccbr1431_001.tar.filelist
        ccbr1431.tar_0001      -> ccbr1431_001.tar_0001
    """
    dot = name.find(".")
    if dot == -1:
        return f"{name}_{n:03d}"
    return f"{name[:dot]}_{n:03d}{name[dot:]}"


def _resolve_tarname(tarname, datatype_collection):
    """Return tarname unchanged if no conflict exists in HPC-DME, otherwise return
    the name with the lowest free _NNN counter inserted before the first extension.

    A conflict exists when either the base tarball (e.g. ccbr982.tar) **or** its
    first split chunk (e.g. ccbr982.tar_0001) already exists in the collection.
    The latter covers prior deposits whose tarball was large enough to be split,
    in which case the base name never lands in HPC-DME as a data object.
    """

    def _name_is_taken(name):
        if _dataobject_exists(f"{datatype_collection}/{name}"):
            return True
        first_chunk = f"{name}_0001"
        return _dataobject_exists(f"{datatype_collection}/{first_chunk}")

    if not _name_is_taken(tarname):
        _info(f"No name conflict found for {tarname!r} in HPC-DME.")
        return tarname
    for n in range(1, 1000):
        candidate = _insert_counter(tarname, n)
        if not _name_is_taken(candidate):
            _info(
                f"Name conflict: {tarname!r} already exists in HPC-DME. "
                f"Using {candidate!r} instead."
            )
            return candidate
    raise RuntimeError(
        f"Could not find a free name for {tarname!r} in {datatype_collection} after 999 attempts."
    )


def _register_collection(collection_path, collection_type, extra_metadata=None):
    payload = {
        "metadataEntries": [{"attribute": "collection_type", "value": collection_type}]
    }
    if extra_metadata:
        payload["metadataEntries"].extend(extra_metadata)
    with NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(payload, tmp, indent=2)
        temp_json = tmp.name

    _info(f"Collection registration payload:\n{json.dumps(payload, indent=2)}")
    try:
        cmd = f"dm_register_collection {shlex.quote(temp_json)} {shlex.quote(collection_path)}"
        run_dm_cmd(
            dm_cmd=cmd, errormsg=f"Failed to create collection {collection_path}"
        )
    finally:
        if os.path.exists(temp_json):
            os.remove(temp_json)


def _ensure_deposit_collections(base_collection, datatype, project_number):
    datatype_collection = f"{base_collection}/{datatype}"
    _info(f"Step 3: verifying destination collection: {datatype_collection}")
    if _collection_exists(datatype_collection):
        _info("Destination datatype collection already exists.")
        return datatype_collection

    _info(f"Datatype collection missing: {datatype_collection}")
    if not _collection_exists(base_collection):
        _info(f"Project collection missing: {base_collection}")
        _info("Creating project collection first ...")
        project_label = f"CCBR-{project_number}"
        today = datetime.now().strftime("%Y%m%d")
        project_metadata = [
            {"attribute": "project_title", "value": project_label},
            {"attribute": "project_description", "value": project_label},
            {"attribute": "origin", "value": "CCBR"},
            {"attribute": "method", "value": "NGS"},
            {"attribute": "access", "value": "Open Access"},
            {"attribute": "organism", "value": "unknown"},
            {"attribute": "summary_of_samples", "value": "unknown"},
            {
                "attribute": "project_start_date",
                "value": today,
                "dateFormat": "yyyyMMdd",
            },
        ]
        _register_collection(
            base_collection, "Project", extra_metadata=project_metadata
        )
    else:
        _info("Project collection exists.")

    _info(f"Creating datatype collection: {datatype_collection}")
    # DME valid collection_type values: [Project, PI_Lab, Sample, Analysis].
    # "Rawdata" is not a valid type, so map it to "Analysis".
    datatype_collection_type = "Analysis" if datatype == "Rawdata" else datatype
    today = datetime.now().strftime("%Y%m%d")
    datatype_metadata = [
        {"attribute": "project_start_date", "value": today, "dateFormat": "yyyyMMdd"},
        {"attribute": "method", "value": "NGS"},
        {"attribute": "number_of_cases", "value": "unknown"},
    ]
    _register_collection(
        datatype_collection, datatype_collection_type, extra_metadata=datatype_metadata
    )
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

    _info(
        f"Tar size is > {split_size_gb:g}GB; splitting into {split_size_gb:g}GB chunks ..."
    )
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
    _info(
        "Checking for tmux/screen/Open OnDemand graphical session for long-running deposit ..."
    )
    _require_terminal_multiplexer()
    _ok("Session check passed (inside tmux/screen/Open OnDemand graphical session).")
    _print_hpcdme_properties()
    if not _check_no_proxy_settings():
        return 1

    source_folder = _resolve_existing_directory(args.folder)
    project_tag = _project_tag(args.projectnumber)
    base_collection = _project_collection_path(args.projectnumber)
    datatype = args.datatype
    datatype_collection = _ensure_deposit_collections(
        base_collection, datatype, args.projectnumber
    )

    scratch_root, datatype_dir = _prepare_scratch_dirs(project_tag, datatype)

    tarname = args.tarname if args.tarname else _default_tarname(args.projectnumber)
    if "/" in tarname:
        return _error("--tarname must be a file name, not a path.")
    _info("Checking for tar file name conflict in HPC-DME destination collection ...")
    tarname = _resolve_tarname(tarname, datatype_collection)
    tar_path = datatype_dir / tarname

    _step(5, f"creating tarball from folder: {source_folder}")
    _info(f"Tar output path: {tar_path}")
    createtar(str(source_folder), str(tar_path))
    _ok(f"Created: {tar_path}")
    _ok(f"Created: {tar_path}.filelist")

    _split_if_needed(tar_path, args.split_size_gb)
    _write_md5_files(datatype_dir)

    _step(6, "transferring staged directory to HPC-DME ...")
    src_dir = f"{datatype_dir}/"
    dst_dir = f"{datatype_collection}/"
    exclude_file = None
    try:
        with NamedTemporaryFile("w", suffix=".exclude", delete=False) as ef:
            ef.write(".*\n**/.*\n")
            exclude_file = ef.name
        cmd = (
            f"dm_register_directory -c -r -t 4 -s"
            f" -e {shlex.quote(exclude_file)}"
            f" {shlex.quote(src_dir)} {shlex.quote(dst_dir)}"
        )
        run_dm_cmd(dm_cmd=cmd, errormsg="dm_register_directory failed during deposit.")
    finally:
        if exclude_file and os.path.exists(exclude_file):
            os.remove(exclude_file)
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
        raise ValueError(
            "--filenames must contain at least one comma-separated file name."
        )
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
    _info(
        "Checking for tmux/screen/Open OnDemand graphical session for long-running retrieve ..."
    )
    _require_terminal_multiplexer()
    _ok("Session check passed (inside tmux/screen/Open OnDemand graphical session).")

    base_collection = _project_collection_path(args.projectnumber)
    datatype = args.datatype
    datatype_collection = _ensure_retrieve_collections(base_collection, datatype)

    project_tag = _project_tag(args.projectnumber)
    user = os.environ.get("USER", "")
    if not user:
        return _error("USER environment variable is not set.")

    if args.folder:
        base_local = _resolve_output_directory(args.folder)
    else:
        base_local = (Path("/scratch") / user / project_tag).resolve()
    target_dir = base_local / datatype
    target_dir.mkdir(parents=True, exist_ok=True)
    _step(4, f"local download directory: {target_dir}")

    # Fetch the full object listing once — used for existence checks and split
    # detection, replacing N serial dm_get_dataobject calls with a single query.
    _step(5, "fetching object listing from HPC-DME ...")
    all_objects = _query_all_dataobjects(datatype_collection)
    known_names = {Path(p).name for p, _s, _d, _dt in all_objects}
    _info(f"{len(known_names)} object(s) found in {datatype_collection}.")

    # Detect split tar parts and warn/auto-set unsplit
    split_names = {n for n in known_names if re.search(r"\.tar_\d{4}$", n)}
    if split_names and not args.unspilt:
        _info(
            "Split tar parts detected in the collection "
            f"({', '.join(sorted(split_names))}). "
            "Pass --unsplit to automatically merge them after download."
        )

    if args.filenames:
        _step(6, "parsing requested filenames ...")
        filenames = _parse_filenames(args.filenames)

        _step(7, "verifying all requested objects exist ...")
        missing = [f for f in filenames if f not in known_names]
        for filename in filenames:
            _info(f"  - {filename}: {'FOUND' if filename in known_names else 'MISSING'}")
        if missing:
            return _error(f"Cannot proceed; missing object(s): {', '.join(missing)}")

        _step(8, "downloading requested objects ...")
        for filename in filenames:
            object_path = f"{datatype_collection}/{filename}"
            cmd = f"dm_download_dataobject {shlex.quote(object_path)} {shlex.quote(str(target_dir))}"
            run_dm_cmd(dm_cmd=cmd, errormsg=f"Failed to download {filename}")
            _ok(f"Downloaded: {filename}")
    else:
        _step(6, "no --filenames provided; full collection mode selected.")
        _step(7, "downloading full collection ...")
        # Download the datatype collection under base_local so we get:
        # <base_local>/<datatype>/...
        # and avoid nested paths like <base_local>/<datatype>/<datatype>/...
        cmd = f"dm_download_collection {shlex.quote(datatype_collection)} {shlex.quote(str(base_local))}"
        run_dm_cmd(
            dm_cmd=cmd, errormsg=f"Failed to download collection {datatype_collection}"
        )
        _ok(f"Downloaded full collection: {datatype_collection}")
        _step(8, "per-file verification skipped in full collection mode.")

    if args.unspilt:
        _step(9, "--unspilt requested; checking for tar parts to merge ...")
        _merge_split_tar_parts(target_dir)
    else:
        _step(9, "--unspilt not requested; skipping merge step.")

    _ok("Retrieve workflow finished successfully.")
    return 0


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


def _parse_deposit_date(raw_value):
    """Parse data_transfer_completed (e.g. '06-25-2026 01:30:16') → 'YYMMDD'.
    Returns None if the value cannot be parsed.
    """
    if not raw_value:
        return None
    for fmt in ("%m-%d-%Y %H:%M:%S", "%m-%d-%Y"):
        try:
            return datetime.strptime(str(raw_value).strip(), fmt).strftime("%y%m%d")
        except ValueError:
            pass
    return None


def _query_all_dataobjects(project_path):
    """Return a list of (absolute_path, size_bytes, depositor, deposit_date) for
    every data object under *project_path*, iterating through all pages.

    *depositor* is the display name of the registering user (registered_by_name)
    falling back to their userid (registered_by), or None if unavailable.
    *deposit_date* is data_transfer_completed formatted as YYMMDD, or None.
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
                f" {shlex.quote(criteria_file)} {shlex.quote(project_path)}"
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
            _info("dm_query_dataobject returned non-zero; no objects found or query failed.")
            break

        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, AttributeError):
            _info("Could not parse dm_query_dataobject output as JSON.")
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
                    deposit_date = _parse_deposit_date(entry["value"])
            depositor = depositor_name or depositor_id
            if abs_path:
                objects.append((abs_path, size, depositor, deposit_date))

        total = data.get("totalCount", 0) or 0
        limit = data.get("limit", 100) or 100
        if page * limit >= total:
            break
        page += 1

    return objects


def _render_ls_tree(project_path, objects):
    """Print a tree of *objects* grouped by their immediate parent sub-collection."""
    # Group objects by their direct parent path (sub-collection)
    sub_collections: dict[str, list[tuple[str, int | None, str | None, str | None]]] = {}
    for abs_path, size, depositor, deposit_date in objects:
        parent = str(Path(abs_path).parent)
        sub_collections.setdefault(parent, []).append((abs_path, size, depositor, deposit_date))

    # Compute sub-collection sizes (sum of known object sizes)
    def _sub_size(items):
        total = 0
        for _, s, _d, _dt in items:
            if s is None:
                return None
            total += s
        return total

    # Project header — use the short name (last path component)
    project_name = Path(project_path).name
    total_all = sum(s for _, s, _d, _dt in objects if s is not None) if objects else 0
    print(f"{project_name}  ({_human_size(total_all)})")

    sorted_subs = sorted(sub_collections.keys())
    for sub_idx, sub_path in enumerate(sorted_subs):
        is_last_sub = sub_idx == len(sorted_subs) - 1
        sub_connector = "└──" if is_last_sub else "├──"
        sub_name = Path(sub_path).name
        sub_sz = _sub_size(sub_collections[sub_path])
        sub_sz_str = f"  ({_human_size(sub_sz)})" if sub_sz is not None else ""
        print(f"{sub_connector} {sub_name}/{sub_sz_str}")

        child_prefix = "    " if is_last_sub else "│   "
        items = sorted(sub_collections[sub_path], key=lambda x: Path(x[0]).name)
        for item_idx, (abs_path, size, depositor, deposit_date) in enumerate(items):
            is_last_item = item_idx == len(items) - 1
            item_connector = "└──" if is_last_item else "├──"
            fname = Path(abs_path).name
            sz_str = _human_size(size) if size is not None else "unknown"
            dep_col = ",".join(filter(None, [depositor, deposit_date])) or ""
            print(f"{child_prefix}{item_connector} {fname:<50}  {sz_str:<12}  {dep_col}")


def _run_ls(args):
    _print_hpcdme_properties()

    project_number = args.projectnumber
    project_path = _project_collection_path(project_number)
    _info(f"Listing HPC-DME collection: {project_path}")
    _info(
        "Note: the DME search index may lag up to 60 minutes behind recent deposits."
    )

    _step(1, f"verifying project collection exists: {project_path}")
    if not _collection_exists(project_path):
        return _error(
            f"Project collection does not exist in HPC-DME: {project_path}"
        )
    _ok("Project collection found.")

    _step(2, "querying data objects ...")
    objects = _query_all_dataobjects(project_path)
    _ok(f"{len(objects)} object(s) found.")

    if not objects:
        _info("No data objects found under this project collection.")
        return 0

    print()
    _render_ls_tree(project_path, objects)
    print()
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
    parser_deposit.add_argument(
        "-f", "--folder", required=True, help="Folder to archive"
    )
    parser_deposit.add_argument(
        "-p",
        "--projectnumber",
        "--project-number",
        type=_normalize_project_number,
        required=True,
        help="Project number (e.g. 1234, abcd, ccbr1234, CCBR-abcd)",
    )
    parser_deposit.add_argument(
        "-d",
        "--datatype",
        type=_normalize_datatype,
        default="Analysis",
        help="Analysis or Rawdata (case-insensitive). Default: Analysis",
    )
    parser_deposit.add_argument(
        "-t",
        "--tarname",
        default="",
        help="Optional tar file name override (default: ccbr<projectnumber>.tar)",
    )
    parser_deposit.add_argument(
        "-s",
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
        "-k",
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
        "-f",
        "--folder",
        default="",
        help="Local base folder (default: /scratch/$USER/CCBR-<projectnumber>)",
    )
    parser_retrieve.add_argument(
        "-p",
        "--projectnumber",
        "--project-number",
        type=_normalize_project_number,
        required=True,
        help="Project number (e.g. 1234, abcd, ccbr1234, CCBR-abcd)",
    )
    parser_retrieve.add_argument(
        "-d",
        "--datatype",
        type=_normalize_datatype,
        default="Analysis",
        help="Analysis or Rawdata (case-insensitive). Default: Analysis",
    )
    parser_retrieve.add_argument(
        "-n",
        "--filenames",
        required=False,
        default="",
        help="Comma-separated file names to retrieve (omit to download full collection)",
    )
    parser_retrieve.add_argument(
        "-u",
        "--unspilt",
        "--unsplit",
        action="store_true",
        help="Merge split parts (*.tar_0001, *.tar_0002, ...) into a tar after download",
    )

    parser_ls = subparsers.add_parser(
        "ls",
        help="List data objects in /CCBR_Archive/GRIDFTP/Project_CCBR-<projectnumber>",
    )
    parser_ls.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"projark is part of parkit; parkit version: {__version__}",
    )
    parser_ls.add_argument(
        "projectnumber",
        metavar="PROJECTNUMBER",
        type=_normalize_project_number,
        help="Project number (e.g. 982, ccbr982, CCBR-982)",
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    start_time = datetime.now().astimezone()
    return_code = 1
    error_message = ""

    try:
        if args.command == "deposit":
            return_code = _run_deposit(args)
        elif args.command == "retrieve":
            return_code = _run_retrieve(args)
        elif args.command == "ls":
            return_code = _run_ls(args)
        else:
            parser.print_help()
            return_code = 1
    except KeyboardInterrupt:
        _info("Interrupted by user.")
        return_code = 130
        error_message = "Interrupted by user."
    except Exception as exc:
        error_message = str(exc)
        return_code = _error(error_message)

    end_time = datetime.now().astimezone()
    status = "SUCCESS" if return_code == 0 else "FAILED"
    if args.command != "ls":
        _send_notification_email(
            args=args,
            status=status,
            return_code=return_code,
            start_time=start_time,
            end_time=end_time,
            error_message=error_message,
        )

    sys.exit(return_code)


if __name__ == "__main__":
    main()
