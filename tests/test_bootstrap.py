"""Tests for environment defaults during Parkit initialization."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("host", ["helix", "biowulf"])
@pytest.mark.parametrize("configured_version", [None, "21"])
def test_java_version_bootstrap(tmp_path, host, configured_version):
    """Default to Java 25 without overriding an explicitly configured version."""
    env = os.environ.copy()
    env["HPC_DM_UTILS"] = str(tmp_path)
    env["HOSTNAME"] = "helix.nih.gov" if host == "helix" else "compute-node"
    env.pop("HPC_DM_JAVA_VERSION", None)
    if configured_version is not None:
        env["HPC_DM_JAVA_VERSION"] = configured_version
    if host == "biowulf":
        scontrol = tmp_path / "scontrol"
        scontrol.write_text("#!/bin/sh\necho biowulf\n")
        scontrol.chmod(0o755)
        env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, parkit; print('JAVA_VERSION=' + os.environ['HPC_DM_JAVA_VERSION'])",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"JAVA_VERSION={configured_version or '25'}" in result.stdout
    if configured_version is None:
        assert "HPC_DM_JAVA_VERSION is not set, setting it to 25" in result.stdout
    else:
        assert "HPC_DM_JAVA_VERSION is not set" not in result.stdout
