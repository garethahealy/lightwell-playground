#!/usr/bin/env python3
"""Unit tests for http_pool download helpers + OSV parsing.

Run: python3 .cursor/skills/lightwell-shared/scripts/test_http_download.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lightwell_shared.download_http import HttpAuthError, header_value  # noqa: E402
from lightwell_shared.fetch_osv import parse_manifest  # noqa: E402
from lightwell_shared.lightwell_urls import provenance_bundle_url  # noqa: E402


def test_parse_manifest() -> None:
    raw = "\n".join(
        [
            "RHSA-1.json,abc123,1",
            "bad name.json,x,1",
            "ok-2.json,def456,99",
            "",
        ]
    )
    entries = parse_manifest(raw)
    assert entries == [("RHSA-1.json", "abc123"), ("ok-2.json", "def456")]


def test_provenance_url() -> None:
    url = provenance_bundle_url(
        "remediated", "org.json", "json", "20220320.0.0.rhlw-00003"
    )
    assert url.endswith(
        "/java/remediated/org/json/json/20220320.0.0.rhlw-00003/"
        "json-20220320.0.0.rhlw-00003.provenance.sigstore.json"
    )


def test_header_value_case() -> None:
    assert header_value({"ETag": '"abc"'}, "etag") == '"abc"'
    assert header_value({"etag": "x"}, "ETag") == "x"


def test_auth_error_message() -> None:
    err = HttpAuthError(403)
    assert "AUTH_FAILED" in str(err)
    assert "403" in str(err)


def main() -> int:
    test_parse_manifest()
    test_provenance_url()
    test_header_value_case()
    test_auth_error_message()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
