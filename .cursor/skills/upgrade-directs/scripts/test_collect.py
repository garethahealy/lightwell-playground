#!/usr/bin/env python3
"""Unit tests for upgrade-directs collect_one MISSING → suggested-catalog-latest.

Run: python3 .cursor/skills/upgrade-directs/scripts/test_collect.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
_COLLECT_PATH = _SCRIPTS / "collect.py"


def _load_collect():
    spec = importlib.util.spec_from_file_location("upgrade_directs_collect", _COLLECT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collect = _load_collect()


def _dep(**kwargs: Any) -> dict:
    base = {
        "groupId": "org.example",
        "artifactId": "demo",
        "version": "1.0.0",
        "catalog": "remediated",
        "property": None,
    }
    base.update(kwargs)
    return base


def _run(dep: dict, resolve, *, take_latest: bool = False) -> dict:
    return collect.collect_one(
        dep,
        take_latest=take_latest,
        cache_root=None,
        ttl=0,
        username="u",
        token="t",
        resolve=resolve,
    )


def test_remediated_same_base_auto_upgrades() -> None:
    def resolve(catalog, g, a, *, tag, same_base_current, **_kw):
        if catalog == "remediated" and same_base_current == "1.2.3":
            return "1.2.3.rhlw-00002"
        raise AssertionError(f"unexpected resolve: {catalog=} {tag=} {same_base_current=}")

    row = _run(_dep(catalog="remediated", version="1.2.3"), resolve)
    assert row["action"] == "UPGRADE"
    assert row["to"] == "1.2.3.rhlw-00002"
    assert row["catalog"] == "remediated"


def test_remediated_same_base_miss_suggests_remediated_latest() -> None:
    calls: list[tuple] = []

    def resolve(catalog, g, a, *, tag, same_base_current, **_kw):
        calls.append((catalog, tag, same_base_current))
        if catalog == "remediated" and same_base_current == "1.0.0":
            return None
        if catalog == "remediated" and tag == "latest":
            return "2.0.0.rhlw-00001"
        raise AssertionError(f"unexpected resolve: {catalog=} {tag=} {same_base_current=}")

    row = _run(_dep(catalog="remediated", version="1.0.0"), resolve, take_latest=True)
    assert row["action"] == "ASK"
    assert row["to"] == "2.0.0.rhlw-00001"
    assert row["catalog"] == "remediated"
    assert row["reason"] == "suggested-catalog-latest"
    assert ("remediated", None, "1.0.0") in calls
    assert ("remediated", "latest", None) in calls


def test_both_catalogs_miss_stays_missing() -> None:
    def resolve(*_a, **_kw):
        return None

    row = _run(_dep(catalog="remediated", version="1.0.0"), resolve)
    assert row["action"] == "MISSING"
    assert row["to"] is None
    assert row["reason"] == "no-lightwell-metadata"


def test_latest_not_newer_keeps() -> None:
    def resolve(catalog, g, a, *, tag, same_base_current, **_kw):
        if same_base_current is not None:
            return None
        if catalog == "remediated" and tag == "latest":
            return "0.9.0"
        if catalog == "validated" and tag == "latest":
            return None
        return None

    row = _run(_dep(catalog="remediated", version="1.0.0"), resolve)
    assert row["action"] == "KEEP"
    assert row["reason"] == "candidate-not-newer"
    assert row["candidate"] == "0.9.0"
    assert row["to"] == "1.0.0"
    assert row["catalog"] == "remediated"


def test_validated_primary_miss_tries_remediated_latest_only() -> None:
    calls: list[tuple] = []

    def resolve(catalog, g, a, *, tag, same_base_current, **_kw):
        calls.append((catalog, tag, same_base_current))
        if catalog == "validated" and tag == "latest":
            return None
        if catalog == "remediated" and tag == "latest":
            return "3.1.0.rhlw-00002"
        raise AssertionError(f"unexpected resolve: {catalog=} {tag=} {same_base_current=}")

    row = _run(_dep(catalog="validated", version="1.0.0"), resolve)
    assert row["action"] == "ASK"
    assert row["reason"] == "suggested-catalog-latest"
    assert row["catalog"] == "remediated"
    assert row["to"] == "3.1.0.rhlw-00002"
    assert calls.count(("validated", "latest", None)) == 1
    assert ("remediated", "latest", None) in calls


def main() -> int:
    test_remediated_same_base_auto_upgrades()
    test_remediated_same_base_miss_suggests_remediated_latest()
    test_both_catalogs_miss_stays_missing()
    test_latest_not_newer_keeps()
    test_validated_primary_miss_tries_remediated_latest_only()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
