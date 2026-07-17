#!/usr/bin/env python3
"""Apply phase: edit pom.xml from direct Collect results, then mvn clean install.

Usage:
  apply.py --from-collect collect.json
  apply.py --from-collect collect.json --include-ask
  apply.py --from-collect collect.json --skip-build --dry-run

Requires Python 3.14+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lightwell-shared" / "scripts"))

from lightwell_shared.apply_common import apply_rows, finish_apply, load_collect  # noqa: E402
from lightwell_shared.pom_edit import apply_direct_collect_row  # noqa: E402
from lightwell_shared.schema import SchemaError  # noqa: E402


def prepare_ask_row(row: dict) -> dict:
    """Map ASK → UPGRADE when user approved via --include-ask."""
    if row.get("action") != "ASK":
        return row
    out = dict(row)
    out["action"] = "UPGRADE"
    out["collectAction"] = "ASK"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply phase: bump direct deps from Collect JSON."
    )
    parser.add_argument("--from-collect", required=True)
    parser.add_argument("--include-ask", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--settings", default=".m2/settings.xml")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args()

    try:
        collect, pom_path = load_collect(args.from_collect)
    except (FileNotFoundError, SchemaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    original = pom_path.read_text(encoding="utf-8")

    def should_apply(row: dict) -> bool:
        action = row.get("action")
        return action == "UPGRADE" or (action == "ASK" and args.include_ask)

    def mutator(text: str, row: dict) -> str:
        if not row.get("to"):
            raise ValueError("no-target")
        return apply_direct_collect_row(text, row)

    text, applied, skipped = apply_rows(
        original,
        list(collect.get("results") or []),
        should_apply=should_apply,
        mutator=mutator,
        prepare_row=prepare_ask_row if args.include_ask else None,
        dry_run=args.dry_run,
    )

    return finish_apply(
        pom_path=pom_path,
        original=original,
        text=text,
        applied=applied,
        skipped=skipped,
        dry_run=args.dry_run,
        skip_build=args.skip_build,
        settings=args.settings,
        repo_root=None,
        output=args.output,
        noun="bump",
    )


if __name__ == "__main__":
    raise SystemExit(main())
