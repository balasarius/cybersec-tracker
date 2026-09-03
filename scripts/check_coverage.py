# SPDX-License-Identifier: Apache-2.0
"""Enforce independent statement and branch coverage thresholds."""

import json
import sys
from pathlib import Path
from typing import TypedDict


class Totals(TypedDict):
    covered_lines: int
    num_statements: int
    covered_branches: int
    num_branches: int


def percentage(covered: int, total: int) -> float:
    return 100.0 if total == 0 else covered * 100.0 / total


def main() -> int:
    payload = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    totals: Totals = payload["totals"]
    statements = percentage(totals["covered_lines"], totals["num_statements"])
    branches = percentage(totals["covered_branches"], totals["num_branches"])
    sys.stdout.write(f"Statement coverage: {statements:.2f}% (required: 90.00%)\n")
    sys.stdout.write(f"Branch coverage: {branches:.2f}% (required: 85.00%)\n")
    return 0 if statements >= 90.0 and branches >= 85.0 else 1


if __name__ == "__main__":
    sys.exit(main())
