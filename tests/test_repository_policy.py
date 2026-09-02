# SPDX-License-Identifier: Apache-2.0
"""Repository policy checks kept executable in local and CI workflows."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")


def test_first_party_python_files_declare_apache_spdx() -> None:
    source_roots = ["apps", "config", "connectors", "destination_adapters", "sdk"]
    missing = [
        str(path.relative_to(ROOT))
        for source_root in source_roots
        for path in (ROOT / source_root).rglob("*.py")
        if "SPDX-License-Identifier: Apache-2.0" not in path.read_text(encoding="utf-8")
    ]

    assert missing == []


def test_relative_markdown_links_resolve() -> None:
    missing: list[str] = []
    for document in ROOT.rglob("*.md"):
        if any(part.startswith(".") for part in document.relative_to(ROOT).parts):
            continue
        for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = document.parent / unquote(target)
            if not resolved.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")

    assert missing == []
