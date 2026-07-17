#!/usr/bin/env python3
"""Unit tests for pom_lib tree helpers and SemVer policy.

Run: python3 .cursor/skills/lightwell-shared/scripts/test_pom_lib.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lightwell_shared.pom_lib import (  # noqa: E402
    ask_reason,
    indexes_by_via_direct,
    is_newer,
    needs_ask,
    semver_triple,
    versions_by_ga,
)
from lightwell_shared.resolve_metadata import highest_rhlw_on_base  # noqa: E402

# Two parents in one tree (single-shot natural shape)
COMBINED = """\
tmp.lightwell:natural-check:jar:0.0.0
+- parent.one:a:jar:1.0:compile
|  +- dep:x:jar:9.0:compile
|  \\- dep:y:war:8.0:compile
\\- parent.two:b:bundle:2.0:compile
   \\- dep:x:jar:9.1:compile (omitted for duplicate)
"""


def test_indexes_by_via_direct() -> None:
    by_via = indexes_by_via_direct(COMBINED)
    assert "parent.one:a" in by_via
    assert "parent.two:b" in by_via
    assert by_via["parent.one:a"]["dep:x"] == "9.0"
    assert by_via["parent.one:a"]["dep:y"] == "8.0"
    assert by_via["parent.two:b"]["dep:x"] == "9.1"
    # Parent GA itself is indexed under its via_direct (= self at depth 1)
    assert by_via["parent.one:a"]["parent.one:a"] == "1.0"


def test_versions_by_ga_first_wins() -> None:
    v = versions_by_ga(COMBINED)
    assert v["dep:x"] == "9.0"
    assert v["dep:y"] == "8.0"


def test_semver_triple() -> None:
    assert semver_triple("1.2.3") == (1, 2, 3)
    assert semver_triple("1.2.3.rhlw-00001") == (1, 2, 3)
    assert semver_triple("20220320") == (20220320, 0, 0)
    assert semver_triple("20220320.0.0.rhlw-00003") == (20220320, 0, 0)
    assert semver_triple("${foo}") is None


def test_never_downgrade() -> None:
    assert is_newer("1.2.4", "1.2.3")
    assert not is_newer("1.2.3", "1.2.4")
    assert not is_newer("1.2.3.rhlw-00001", "1.2.4")
    assert is_newer("1.2.3.rhlw-00002", "1.2.3.rhlw-00001")
    assert is_newer("1.2.3.rhlw-00001", "1.2.3")


def test_needs_ask_semver_policy() -> None:
    g = "org.example"
    # patch increase → auto
    assert not needs_ask(g, "1.2.3", "1.2.4")
    assert not needs_ask(g, "1.2.3", "1.2.4.rhlw-00001")
    # same major.minor.patch (Lightwell build) → auto
    assert not needs_ask(g, "1.2.3", "1.2.3.rhlw-00001")
    assert ask_reason("1.2.3", "1.2.3.rhlw-00001") == "semver-patch-same"
    # minor / major → ASK
    assert needs_ask(g, "1.2.3", "1.3.0")
    assert ask_reason("1.2.3", "1.3.0") == "semver-minor"
    assert needs_ask(g, "1.2.3", "2.0.0")
    assert ask_reason("1.2.3", "2.0.0") == "semver-major"
    # unsure → ASK
    assert needs_ask(g, "weird", "1.0.0")
    assert ask_reason("weird", "1.0.0") == "semver-unsure"


def test_highest_rhlw_semver_base_match() -> None:
    versions = [
        "20220320.0.0.rhlw-00001",
        "20220320.0.0.rhlw-00003",
        "20231013.0.0.rhlw-00001",
    ]
    assert highest_rhlw_on_base(versions, "20220320") == "20220320.0.0.rhlw-00003"
    assert highest_rhlw_on_base(versions, "20220320.0.0") == "20220320.0.0.rhlw-00003"


def main() -> int:
    test_indexes_by_via_direct()
    test_versions_by_ga_first_wins()
    test_semver_triple()
    test_never_downgrade()
    test_needs_ask_semver_policy()
    test_highest_rhlw_semver_base_match()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
