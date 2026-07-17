#!/usr/bin/env python3
"""Summary phase: markdown table + OSV for applied remediated direct bumps.

Usage:
  summary.py --from-collect collect.json --from-apply apply.json
  summary.py --from-collect collect.json --from-apply apply.json --skip-osv

Requires Python 3.14+.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lightwell-shared" / "scripts"))

from lightwell_shared.summary_common import run_upgrade_summary  # noqa: E402


def format_row(r: dict[str, Any], was_applied: bool) -> str:
    action = r.get("action", "")
    if was_applied:
        action = f"{action} (applied)"
    return (
        f"| `{r.get('ga')}` | `{r.get('from')}` | `{r.get('to')}` | "
        f"{r.get('catalog') or ''} | {action} |"
    )


def select_osv(applied_rows: list[dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    bumps: list[tuple[str, str, str, str]] = []
    for r in applied_rows:
        if (
            r.get("catalog") == "remediated" or ".rhlw-" in str(r.get("to") or "")
        ) and r.get("to"):
            bumps.append(
                (r["groupId"], r["artifactId"], str(r.get("from")), str(r["to"]))
            )
    return bumps


def main() -> int:
    return run_upgrade_summary(
        title="## Upgrade directs summary",
        table_headers=["Artifact", "From", "To", "Catalog", "Action"],
        format_collect_row=format_row,
        select_osv_bumps=select_osv,
        osv_heading="### CVEs (remediated bumps)",
        description="Summary phase: table + OSV for direct upgrades.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
