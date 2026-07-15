"""Command line interface tests."""
from __future__ import annotations

import json

from anviksha.cli import main


def test_cli_prints_offline_output(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["2", "+", "3", "*", "4"]) == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == "14.0"
    assert captured.err == ""


def test_cli_prints_json_response(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--json", "2 + 2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "succeeded"
    assert payload["output"] == 4.0
    assert "builtin.calculator" in payload["diagnostics"][0]


def test_cli_returns_usage_error_for_unplannable_goal(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        main(["build", "a", "production", "agent"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover
        raise AssertionError("expected SystemExit")

    assert "no capability registered" in capsys.readouterr().err
