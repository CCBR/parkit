import pytest
import subprocess


def test_help():
    output = subprocess.run(
        "parkit --help", capture_output=True, shell=True, text=True
    ).stdout
    assert "ERROR:HPC_DM_UTILS in unset!" in output
