#!/usr/bin/env python3
"""Unit tests for pom_edit helpers (sample pom.xml style).

Run: python3 .cursor/skills/lightwell-shared/scripts/test_pom_edit.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lightwell_shared.pom_edit import (  # noqa: E402
    bump_direct_dependency,
    ensure_exclusion_on_parent,
    pretty_print_pom,
    remove_exclusion_from_parent,
    remove_promoted_dependency,
    upsert_promoted_dependency,
)

SAMPLE = """\
<?xml version="1.0"?>
<project>
    <dependencies>
        <!-- Source: https://packages.redhat.com/api/pulp-content/public-lightwell-demo/java/remediated/ -->
        <dependency>
            <groupId>org.json</groupId>
            <artifactId>json</artifactId>
            <version>20220320.0.0.rhlw-00001</version>
        </dependency>
        <dependency>
            <groupId>commons-fileupload</groupId>
            <artifactId>commons-fileupload</artifactId>
            <version>1.5</version>
            <exclusions>
                <exclusion>
                    <groupId>commons-io</groupId>
                    <artifactId>commons-io</artifactId>
                </exclusion>
            </exclusions>
        </dependency>
        <!-- Transitive of commons-fileupload:commons-fileupload -->
        <!-- Source: https://packages.redhat.com/api/pulp-content/public-lightwell-demo/java/remediated/ -->
        <dependency>
            <groupId>commons-io</groupId>
            <artifactId>commons-io</artifactId>
            <version>2.11.0.rhlw-00001</version>
        </dependency>
    </dependencies>
</project>
"""


def main() -> int:
    bumped = bump_direct_dependency(
        SAMPLE, "org.json", "json", "20220320.0.0.rhlw-00099", catalog="remediated"
    )
    assert "rhlw-00099" in bumped
    assert "org.json" in bumped

    updated = upsert_promoted_dependency(
        bumped,
        "commons-io",
        "commons-io",
        "2.11.0.rhlw-00002",
        ["commons-fileupload:commons-fileupload"],
    )
    assert "rhlw-00002" in updated
    assert "Transitive of commons-fileupload:commons-fileupload" in updated

    dropped = remove_promoted_dependency(updated, "commons-io", "commons-io")
    assert "<!-- Transitive of commons-fileupload" not in dropped
    # Parent may still exclude commons-io; only the promoted declare is gone
    assert "Transitive of" not in dropped

    no_excl = remove_exclusion_from_parent(
        dropped, "commons-fileupload:commons-fileupload", "commons-io", "commons-io"
    )
    assert "commons-io" not in no_excl or "<exclusion>" not in no_excl

    with_excl = ensure_exclusion_on_parent(
        no_excl, "commons-fileupload:commons-fileupload", "commons-io", "commons-io"
    )
    assert "<exclusion>" in with_excl
    assert "commons-io" in with_excl

    try:
        ensure_exclusion_on_parent(no_excl, "missing:parent", "commons-io", "commons-io")
        raise AssertionError("expected ValueError for missing parent")
    except ValueError as exc:
        assert "parent dependency not found" in str(exc)

    # Mutations keep dependency tag indentation (no column-0 <dependency>).
    assert re.search(r"(?m)^[ \t]+<dependency>", bumped)
    assert not re.search(r"(?m)^<dependency>", bumped)
    assert re.search(r"(?m)^[ \t]+</dependency>", with_excl)
    assert not re.search(r"(?m)^</dependency>", with_excl)

    messy = """\
<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <!-- Source: https://example.invalid/remediated/ -->
<dependency>
            <groupId>org.json</groupId>
            <artifactId>json</artifactId>
            <version>1</version>
        </dependency>
</dependencies>
</project>
"""
    pretty = pretty_print_pom(messy)
    assert pretty == pretty_print_pom(pretty)  # idempotent
    assert "    <dependencies>\n" in pretty
    assert "        <dependency>\n" in pretty
    assert "            <groupId>org.json</groupId>\n" in pretty
    assert "        </dependency>\n" in pretty
    assert "    </dependencies>\n" in pretty
    assert not re.search(r"(?m)^<dependency>", pretty)
    assert not re.search(r"(?m)^</dependencies>", pretty)

    print("test_pom_edit: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
