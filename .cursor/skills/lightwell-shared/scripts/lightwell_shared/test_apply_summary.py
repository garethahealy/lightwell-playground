#!/usr/bin/env python3
"""Unit tests for apply_common, summary_common, thread_jobs.

Run:
  python3 -m lightwell_shared.test_apply_summary
  # from .cursor/skills/lightwell-shared/scripts
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lightwell_shared.apply_common import apply_rows  # noqa: E402
from lightwell_shared.download_http import HttpAuthError  # noqa: E402
from lightwell_shared.summary_common import OsvAuthError, effective_action, fetch_osv_lines  # noqa: E402
from lightwell_shared.thread_jobs import map_threaded  # noqa: E402


def test_prepare_row_records_effective_action() -> None:
    rows = [
        {
            "action": "ASK",
            "pending": "PROMOTE",
            "ga": "g:a",
            "groupId": "g",
            "artifactId": "a",
            "from": "1.0.0",
            "to": "1.0.0.rhlw-00001",
        }
    ]

    def prepare(row: dict) -> dict:
        out = dict(row)
        out["action"] = row["pending"]
        out["collectAction"] = "ASK"
        return out

    text, applied, skipped = apply_rows(
        "<pom/>",
        rows,
        should_apply=lambda r: r.get("action") == "ASK",
        mutator=lambda t, _r: t,
        prepare_row=prepare,
        dry_run=False,
    )
    assert text == "<pom/>"
    assert not skipped
    assert len(applied) == 1
    assert applied[0]["action"] == "PROMOTE"
    assert applied[0]["appliedAction"] == "PROMOTE"
    assert applied[0]["collectAction"] == "ASK"
    assert effective_action(applied[0]) == "PROMOTE"


def test_map_threaded_order_and_cancel() -> None:
    def work(idx: int, n: int) -> int:
        if n == 2:
            raise RuntimeError("boom")
        return n * 10

    out = map_threaded([1, 3, 4], work, max_workers=2)
    assert out == [10, 30, 40]

    try:
        map_threaded([1, 2, 3], work, max_workers=2, cancel_on=RuntimeError)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "boom" in str(exc)


def test_fetch_osv_auth_failed() -> None:
    with patch(
        "lightwell_shared.summary_common.fetch_osv_lines_for_bumps",
        side_effect=HttpAuthError(403),
    ):
        try:
            fetch_osv_lines([("g", "a", "1", "2")])
            raise AssertionError("expected OsvAuthError")
        except OsvAuthError:
            pass


def main() -> int:
    test_prepare_row_records_effective_action()
    test_map_threaded_order_and_cancel()
    test_fetch_osv_auth_failed()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
