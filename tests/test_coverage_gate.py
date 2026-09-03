# SPDX-License-Identifier: Apache-2.0
"""Tests for the independent statement/branch coverage gate."""

import json

from scripts import check_coverage


def test_percentage_handles_empty_and_non_empty_totals() -> None:
    assert check_coverage.percentage(0, 0) == 100.0
    assert check_coverage.percentage(85, 100) == 85.0


def test_coverage_main_passes_and_fails_thresholds(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    passing = {
        "totals": {
            "covered_lines": 90,
            "num_statements": 100,
            "covered_branches": 85,
            "num_branches": 100,
        }
    }
    monkeypatch.setattr(
        check_coverage.Path, "read_text", lambda *_args, **_kwargs: json.dumps(passing)
    )
    assert check_coverage.main() == 0
    assert "Statement coverage: 90.00%" in capsys.readouterr().out

    failing = {"totals": {**passing["totals"], "covered_branches": 84}}
    monkeypatch.setattr(
        check_coverage.Path, "read_text", lambda *_args, **_kwargs: json.dumps(failing)
    )
    assert check_coverage.main() == 1
