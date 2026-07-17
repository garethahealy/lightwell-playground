#!/usr/bin/env python3
"""Summary phase: markdown table + OSV for applied transitive PROMOTE/UPDATE.

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

from lightwell_shared.summary_common import effective_action, run_upgrade_summary  # noqa: E402


def format_row(r: dict[str, Any], was_applied: bool) -> str:
    action = r.get("action", "")
    if was_applied:
        action = f"{action} (applied)"
    via = ",".join(r.get("via") or []) or "-"
    return (
        f"| `{r.get('ga')}` | `{r.get('from')}` | `{r.get('to')}` | "
        f"`{via}` | {action} |"
    )


def select_osv(applied_rows: list[dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    bumps: list[tuple[str, str, str, str]] = []
    for r in applied_rows:
        action = effective_action(r)
        if action in {"PROMOTE", "UPDATE"} and r.get("to") and r.get("from"):
            bumps.append(
                (r["groupId"], r["artifactId"], str(r["from"]), str(r["to"]))
            )
    return bumps


def main() -> int:
    return run_upgrade_summary(
        title="## Upgrade transitives summary",
        table_headers=["Artifact", "From", "To", "Via", "Action"],
        format_collect_row=format_row,
        select_osv_bumps=select_osv,
        osv_heading="### CVEs (remediated promote/update)",
        description="Summary phase: table + OSV for transitive upgrades.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
