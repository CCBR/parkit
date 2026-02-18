import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("HOSTNAME", "helix.nih.gov")
os.environ.setdefault("HPC_DM_UTILS", "/tmp")
os.environ.setdefault("HPC_DM_JAVA_VERSION", "23.0.2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parkit.src.utils import (
    _cmd_exists,
    check_file_exists,
    check_path,
    create_random_path,
    delete_listoffiles,
    errorout,
    get_md5sum,
    has_write_permission,
    is_folder,
    run_cmd,
    run_dm_cmd,
    warning,
    which,
)


def test_has_write_permission(tmp_path):
    assert has_write_permission(str(tmp_path)) is True


def test_is_folder(tmp_path):
    assert is_folder(str(tmp_path)) is True
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")
    assert is_folder(str(file_path)) is False


def test_check_file_exists(tmp_path):
    file_path = tmp_path / "file.txt"
    assert check_file_exists(str(file_path)) is None
    file_path.write_text("data")
    assert check_file_exists(str(file_path)) is True


def test_cmd_exists_with_custom_path(tmp_path):
    exe_path = tmp_path / "fakecmd"
    exe_path.write_text("#!/bin/sh\necho hi")
    os.chmod(exe_path, 0o755)
    assert _cmd_exists("fakecmd", path=[str(tmp_path)]) is True
    assert _cmd_exists("missingcmd", path=[str(tmp_path)]) is False


def test_check_path_invalid_command():
    with pytest.raises(SystemExit):
        check_path("definitely_missing_cmd_12345")


def test_create_random_path(tmp_path):
    path = create_random_path(str(tmp_path), ".tar")
    assert path.startswith(str(tmp_path))
    assert path.endswith(".tar")


def test_run_cmd_success(capsys):
    run_cmd("echo ok", echocmd=False)
    captured = capsys.readouterr()
    assert "ok" not in captured.out


def test_run_cmd_failure_no_exit():
    run_cmd("false", exitiffails=False, echocmd=False)


def test_run_cmd_failure_exit():
    with pytest.raises(SystemExit):
        run_cmd("false", exitiffails=True, echocmd=False)


def test_delete_listoffiles(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("data")
    delete_listoffiles([str(file_path)])
    assert not file_path.exists()


def test_errorout_and_warning(capsys):
    warning("note")
    captured = capsys.readouterr()
    assert "WARNING:note" in captured.out
    with pytest.raises(SystemExit):
        errorout("boom")
    captured = capsys.readouterr()
    assert "ERROR:boom" in captured.out


def test_get_md5sum(tmp_path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("hello")
    assert get_md5sum(str(file_path)) == "5d41402abc4b2a76b9719d911017c592"


def test_run_dm_cmd_mocked():
    with patch.dict(
        os.environ, {"HPC_DM_JAVA_VERSION": "23.0.2", "HPC_DM_UTILS": "/tmp"}
    ):
        with patch("subprocess.run") as mock_run:
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = "ok"
            proc.stderr = ""
            mock_run.return_value = proc
            result = run_dm_cmd("dm_cmd", returnproc=True)
            assert result.returncode == 0


def test_which():
    assert which("definitely_missing_cmd_12345") is None
