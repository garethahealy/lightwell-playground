#!/usr/bin/env python3
"""Unit tests for http_pool coalescing (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import threading

from lightwell_shared.http_pool import HttpsPool  # noqa: E402


def main() -> int:
    pool = HttpsPool(max_per_host=2, timeout=5.0)
    calls = {"n": 0}
    lock = threading.Lock()

    def fake_uncached(url, *, headers, method):
        with lock:
            calls["n"] += 1
        # Simulate slow origin
        threading.Event().wait(0.05)
        return 200, f"body-{url}", {"ETag": "x"}

    pool._request_uncached = fake_uncached  # type: ignore[method-assign]

    results: list[tuple] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            results.append(pool.request("https://example.test/a", headers={}))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(results) == 12
    assert calls["n"] == 1, f"expected 1 coalesced fetch, got {calls['n']}"
    assert all(r[0] == 200 for r in results)
    print("test_http_pool: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
