#!/usr/bin/env python3
"""Shared helpers for upgrade apply phases (pom write + mvn)."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lightwell_shared.mvn_run import lightwell_download_lines, repo_root_for, run_mvn_clean_install
from lightwell_shared.pom_edit import pretty_print_pom
from lightwell_shared.schema import require_schema, stamp


def write_result(result: dict[str, Any], output: str) -> None:
    text = json.dumps(stamp(result), indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    sys.stdout.write(text)


def finish_apply(
    *,
    pom_path: Path,
    original: str,
    text: str,
    applied: list[dict],
    skipped: list[dict],
    dry_run: bool,
    skip_build: bool,
    settings: str,
    repo_root: Path | None,
    output: str,
    noun: str = "action",
) -> int:
    """Write pom (unless dry-run), optionally build, emit apply JSON. Return exit code.

    On Maven failure: leave pom changes in place for user debugging; exit 1.
    Never reverts the pom.
    """
    result: dict[str, Any] = {
        "pom": str(pom_path.resolve()),
        "applied": applied,
        "skipped": skipped,
        "dryRun": bool(dry_run),
    }

    if dry_run:
        print(
            f"DRY_RUN would apply {len(applied)} {noun}(s); skipped {len(skipped)}",
            file=sys.stderr,
        )
        write_result(result, output)
        return 0

    if text != original:
        text = pretty_print_pom(text)
        pom_path.write_text(text, encoding="utf-8")
        print(f"Updated {pom_path} ({len(applied)} {noun}(s))", file=sys.stderr)
    else:
        print("No pom changes", file=sys.stderr)

    if not skip_build and applied:
        root = repo_root if repo_root and repo_root.is_dir() else repo_root_for(pom_path)
        rc, log = run_mvn_clean_install(root, settings)
        result["build"] = {
            "ok": rc == 0,
            "exitCode": rc,
            "lightwellDownloads": lightwell_download_lines(log),
        }
        if rc != 0:
            print("BUILD_FAILED: pom left for debugging", file=sys.stderr)
            write_result(result, output)
            return 1

    write_result(result, output)
    return 0


def load_collect(path: str) -> tuple[dict, Path]:
    collect = json.loads(Path(path).read_text(encoding="utf-8"))
    require_schema(collect, label=path)
    pom_path = Path(collect.get("pom") or "pom.xml")
    if not pom_path.is_file():
        raise FileNotFoundError(f"pom not found: {pom_path}")
    return collect, pom_path


def apply_rows(
    text: str,
    rows: list[dict],
    *,
    should_apply: Callable[[dict], bool],
    mutator: Callable[[str, dict], str],
    dry_run: bool,
    prepare_row: Callable[[dict], dict] | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """Apply Collect rows. ``prepare_row`` may remap ASK→PROMOTE/UPDATE before mutate.

    Applied entries use the prepared row's ``action`` (and ``appliedAction``) so
    Summary/OSV see the effective action, not the Collect gate token.
    """
    applied: list[dict] = []
    skipped: list[dict] = []
    for row in rows:
        if not should_apply(row):
            skipped.append({**row, "skipReason": f"action={row.get('action')}"})
            continue
        work = prepare_row(row) if prepare_row else row
        applied_action = work.get("action")
        if dry_run:
            applied.append({**work, "appliedAction": applied_action, "dryRun": True})
            continue
        try:
            text = mutator(text, work)
            applied.append({**work, "appliedAction": applied_action})
        except ValueError as exc:
            skipped.append({**row, "skipReason": str(exc)})
    return text, applied, skipped
