import subprocess


def test_help():
    output = subprocess.run(
        "parkit --help", capture_output=True, shell=True, text=True
    ).stdout
    assert "usage: parkit" in output
