#!/usr/bin/env python3
"""Parse Maven dependency bumps from a Renovate PR body.

Reads PR markdown on stdin (or FILE). Prints one line per Maven bump:

  groupId artifactId fromVersion toVersion

Only rows whose package looks like groupId:artifactId (Maven GAV without
version) and whose Change column has `from` → `to` (backticks optional) are
emitted. Non-Maven managers (actions, pre-commit, etc.) are ignored.

Requires Python 3.14+.
"""

from __future__ import annotations

import argparse
import re
import sys

# [groupId:artifactId](url) — Maven coords use one colon between G and A
PACKAGE_RE = re.compile(
    r"\[([A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+)\]\([^)]*\)"
)

# `from` → `to`  or  from → to  (arrow may be HTML entity)
CHANGE_RE = re.compile(
    r"[`]?([^`|\s]+)[`]?\s*(?:→|->|&#8203;→)\s*[`]?([^`|\s]+)[`]?"
)


def strip_cell(cell: str) -> str:
    return " ".join(cell.strip().split())


def parse_body(text: str) -> list[tuple[str, str, str, str]]:
    bumps: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[\s:-]+\|", line):
            continue

        cells = [strip_cell(c) for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue

        pkg_m = PACKAGE_RE.search(cells[0])
        if not pkg_m:
            continue
        package = pkg_m.group(1)
        if package.count(":") != 1:
            continue
        group_id, artifact_id = package.split(":", 1)

        # Prefer the Change column: often index 1, sometimes later
        change_text = ""
        for cell in cells[1:]:
            if "→" in cell or "->" in cell:
                change_text = cell
                break
        if not change_text:
            continue

        # Drop badge image markdown noise; keep version arrow segment
        change_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", change_text)
        ch_m = CHANGE_RE.search(change_text)
        if not ch_m:
            continue
        from_ver, to_ver = ch_m.group(1), ch_m.group(2)
        if from_ver == to_ver:
            continue

        row = (group_id, artifact_id, from_ver, to_ver)
        if row in seen:
            continue
        seen.add(row)
        bumps.append(row)

    return bumps


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse Maven bumps from a Renovate PR body"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="PR body file (default: stdin)",
    )
    parser.add_argument(
        "--rhlw-only",
        action="store_true",
        help="Only emit bumps where from or to contains .rhlw-",
    )
    args = parser.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    else:
        text = sys.stdin.read()

    bumps = parse_body(text)
    if args.rhlw_only:
        bumps = [
            b
            for b in bumps
            if ".rhlw-" in b[2] or ".rhlw-" in b[3]
        ]

    for group_id, artifact_id, from_ver, to_ver in bumps:
        print(f"{group_id} {artifact_id} {from_ver} {to_ver}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
