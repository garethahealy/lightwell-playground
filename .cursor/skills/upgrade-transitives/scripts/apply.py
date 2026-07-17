#!/usr/bin/env python3
"""Apply phase: edit pom.xml from transitive Collect results, then mvn clean install.

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
from lightwell_shared.mvn_run import repo_root_for  # noqa: E402
from lightwell_shared.pom_edit import apply_transitive_collect_row  # noqa: E402
from lightwell_shared.schema import SchemaError  # noqa: E402


def prepare_ask_row(row: dict) -> dict:
    """Map ASK → pending PROMOTE/UPDATE when user approved via --include-ask."""
    if row.get("action") != "ASK":
        return row
    pending = row.get("pending")
    if pending not in {"PROMOTE", "UPDATE"}:
        raise ValueError(f"ASK row missing pending PROMOTE/UPDATE: {row.get('ga')}")
    out = dict(row)
    out["action"] = pending
    out["collectAction"] = "ASK"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply phase: promote/update/drop transitives from Collect JSON."
    )
    parser.add_argument("--from-collect", required=True)
    parser.add_argument(
        "--include-ask",
        action="store_true",
        help="Also apply ASK rows (user approved SemVer bumps)",
    )
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
    allowed = {"PROMOTE", "UPDATE", "KEEP", "DROP"}

    def should_apply(row: dict) -> bool:
        action = row.get("action")
        return action in allowed or (action == "ASK" and args.include_ask)

    text, applied, skipped = apply_rows(
        original,
        list(collect.get("results") or []),
        should_apply=should_apply,
        mutator=apply_transitive_collect_row,
        prepare_row=prepare_ask_row if args.include_ask else None,
        dry_run=args.dry_run,
    )

    root = Path(collect.get("repoRoot") or "")
    if not root.is_dir():
        root = repo_root_for(pom_path)

    return finish_apply(
        pom_path=pom_path,
        original=original,
        text=text,
        applied=applied,
        skipped=skipped,
        dry_run=args.dry_run,
        skip_build=args.skip_build,
        settings=collect.get("settings") or args.settings,
        repo_root=root,
        output=args.output,
        noun="action",
    )


if __name__ == "__main__":
    raise SystemExit(main())
