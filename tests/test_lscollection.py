"""Regression coverage for listing size formats and command-line options."""

import json
import subprocess
import sys

import pytest

from parkit.src import lscollection as listing


@pytest.mark.parametrize(
    "size,expected",
    [
        (0, "0.0 B"),
        (999, "999.0 B"),
        (1000, "1.0 KB"),
        (57743, "57.7 KB"),
        (1000000, "1.0 MB"),
        (536870912000, "536.9 GB"),
    ],
)
def test_decimal_sizes(size, expected):
    assert listing._format_size(size, True) == expected


@pytest.mark.parametrize("human_readable", [False, True])
def test_listing_totals_and_format(monkeypatch, capsys, human_readable):
    objects = [
        ("/project/Analysis/nested/a", 1000, "Alice", "261029"),
        ("/project/Analysis/b", 2000, "Bob", "261029"),
        ("/project/root", 33, None, None),
    ]
    monkeypatch.setattr(listing, "query_all_dataobjects", lambda _: objects)
    assert listing.ls_collection("/project", human_readable=human_readable) == 0
    output = capsys.readouterr().out
    for value in (3033, 3000, 1000, 2000, 33):
        assert listing._format_size(value, human_readable) in output
    assert "Analysis/" in output
    assert "Alice,261029" in output


def test_exact_large_bytes_and_alignment(capsys):
    size = 2**60 + 1
    listing.render_ls_tree(
        "/project",
        [
            ("/project/a", size, "Alice", None),
            ("/project/b", 33, "Bob", None),
        ],
    )
    output = capsys.readouterr().out
    assert f"project  ({size + 33} B)" in output
    assert f"{size} B" in output
    rows = output.splitlines()[1:]
    assert rows[0].index("Alice") == rows[1].index("Bob")


def test_unknown_and_json(capsys):
    objects = [
        ("/project/sub/a", None, None, None),
        ("/project/b", 57743, "Alice", "261029"),
    ]
    listing.render_ls_tree("/project", objects)
    output = capsys.readouterr().out
    assert "unknown" in output
    assert output.splitlines()[0] == "project"
    listing.render_ls_json(objects)
    records = json.loads(capsys.readouterr().out)
    assert records[0]["size_bytes"] is None
    assert records[0]["size_human"] is None
    assert records[1]["size_bytes"] == 57743
    assert records[1]["size_human"] == "57.7 KB"


@pytest.mark.parametrize(
    "module,target", [("parkit", "/project"), ("parkit.projark", "1091")]
)
def test_cli_format_options(module, target):
    command = [sys.executable, "-m", module, "ls", target]
    help_result = subprocess.run(command + ["--help"], capture_output=True, text=True)
    assert help_result.returncode == 0
    assert "--human-readable" in help_result.stdout
    conflict = subprocess.run(
        command + ["--human-readable", "--json"], capture_output=True, text=True
    )
    assert conflict.returncode == 2
    assert "not allowed with argument" in conflict.stderr
