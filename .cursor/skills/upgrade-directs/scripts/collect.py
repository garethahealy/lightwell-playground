#!/usr/bin/env python3
"""Collect phase: Lightwell upgrade candidates for directs (batched, cached).

Usage:
  collect.py --from-plan plan.json
  collect.py --from-plan plan.json --take-latest

Reads LIGHTWELL_USERNAME / LIGHTWELL_TOKEN. Never prints credentials.
Requires Python 3.14+. Does not edit pom.xml.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lightwell-shared" / "scripts"))

from lightwell_shared.pom_lib import ask_reason, is_newer, needs_ask  # noqa: E402
from lightwell_shared.resolve_metadata import (  # noqa: E402
    AuthFailedError,
    MetadataError,
    default_cache_root,
    resolve_payload,
)
from lightwell_shared.schema import SchemaError, require_schema, stamp  # noqa: E402
from lightwell_shared.thread_jobs import map_threaded  # noqa: E402


def try_resolve(
    catalog: str,
    group_id: str,
    artifact_id: str,
    *,
    tag: str | None,
    same_base_current: str | None,
    cache_root: Path | None,
    ttl: int,
    username: str,
    token: str,
) -> str | None:
    try:
        return resolve_payload(
            catalog,
            group_id,
            artifact_id,
            tag=tag,
            same_base_current=same_base_current,
            cache_root=cache_root,
            ttl=ttl,
            username=username,
            token=token,
        )
    except AuthFailedError:
        raise
    except MetadataError:
        return None


def collect_one(
    dep: dict,
    *,
    take_latest: bool,
    cache_root: Path | None,
    ttl: int,
    username: str,
    token: str,
) -> dict:
    g = dep["groupId"]
    a = dep["artifactId"]
    cur = dep["version"]
    catalog = dep.get("catalog") or "unknown"
    property_name = dep.get("property")
    ga = f"{g}:{a}"

    base = {
        "groupId": g,
        "artifactId": a,
        "ga": ga,
        "from": cur,
        "property": property_name,
        "catalog": catalog,
    }

    if not cur or cur.startswith("${"):
        return {**base, "action": "MISSING", "to": None, "reason": "unresolved-version"}

    target: str | None = None
    used_catalog = catalog

    if catalog == "remediated":
        target = try_resolve(
            "remediated",
            g,
            a,
            tag=None,
            same_base_current=cur,
            cache_root=cache_root,
            ttl=ttl,
            username=username,
            token=token,
        )
        used_catalog = "remediated"
    elif catalog == "validated":
        target = try_resolve(
            "validated",
            g,
            a,
            tag="latest",
            same_base_current=None,
            cache_root=cache_root,
            ttl=ttl,
            username=username,
            token=token,
        )
        used_catalog = "validated"
    else:
        # Prefer remediated same-base (CVE backports), then validated latest
        target = try_resolve(
            "remediated",
            g,
            a,
            tag=None,
            same_base_current=cur,
            cache_root=cache_root,
            ttl=ttl,
            username=username,
            token=token,
        )
        if target:
            used_catalog = "remediated"
        else:
            target = try_resolve(
                "validated",
                g,
                a,
                tag="latest",
                same_base_current=None,
                cache_root=cache_root,
                ttl=ttl,
                username=username,
                token=token,
            )
            if target:
                used_catalog = "validated"

    if not target:
        return {
            **base,
            "catalog": used_catalog if used_catalog != "unknown" else catalog,
            "action": "MISSING",
            "to": None,
            "reason": "no-lightwell-metadata",
        }

    if target == cur:
        return {
            **base,
            "catalog": used_catalog,
            "action": "KEEP",
            "to": target,
        }

    # Do not "upgrade" to an older Lightwell pin (e.g. validated latest < current)
    if not is_newer(target, cur):
        return {
            **base,
            "catalog": used_catalog,
            "action": "KEEP",
            "to": cur,
            "reason": "candidate-not-newer",
            "candidate": target,
        }

    if not take_latest and needs_ask(g, cur, target):
        return {
            **base,
            "catalog": used_catalog,
            "action": "ASK",
            "to": target,
            "reason": ask_reason(cur, target),
        }

    return {
        **base,
        "catalog": used_catalog,
        "action": "UPGRADE",
        "to": target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-plan", required=True, help="JSON from plan.py")
    parser.add_argument(
        "--take-latest",
        action="store_true",
        help="Apply SemVer ASK rows (major/minor/same-patch/unsure) without gating",
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument(
        "--ttl",
        type=int,
        default=int(os.environ.get("LIGHTWELL_METADATA_CACHE_TTL", "3600")),
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=int(os.environ.get("LIGHTWELL_METADATA_JOBS", "16")),
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Write JSON results to this path (also prints to stdout)",
    )
    args = parser.parse_args()

    if args.jobs < 1:
        print("error: --jobs must be >= 1", file=sys.stderr)
        return 2

    plan = json.loads(Path(args.from_plan).read_text(encoding="utf-8"))
    try:
        require_schema(plan, label=args.from_plan)
    except SchemaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    username = os.environ.get("LIGHTWELL_USERNAME", "")
    token = os.environ.get("LIGHTWELL_TOKEN", "")
    if not username or not token:
        print("CREDS_MISSING", file=sys.stderr)
        return 1

    deps = plan.get("dependencies") or []
    cache_root = default_cache_root(args.no_cache)

    def work(idx: int, dep: dict) -> dict:
        return collect_one(
            dep,
            take_latest=args.take_latest,
            cache_root=cache_root,
            ttl=args.ttl,
            username=username,
            token=token,
        )

    try:
        rows = map_threaded(
            deps,
            work,
            max_workers=args.jobs,
            cancel_on=AuthFailedError,
        )
    except AuthFailedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out = stamp({"pom": plan.get("pom"), "results": rows})
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    sys.stdout.write(text)

    # Human-readable action lines on stderr for the agent checklist
    for r in rows:
        action = r["action"]
        ga = r["ga"]
        if action == "UPGRADE":
            print(f"UPGRADE {ga} {r['from']} -> {r['to']} catalog={r['catalog']}", file=sys.stderr)
        elif action == "ASK":
            print(
                f"ASK {ga} {r['from']} -> {r['to']} catalog={r['catalog']} reason={r.get('reason')}",
                file=sys.stderr,
            )
        elif action == "KEEP":
            print(f"KEEP {ga} {r['from']} catalog={r['catalog']}", file=sys.stderr)
        else:
            print(
                f"MISSING {ga} {r['from']} reason={r.get('reason')}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
