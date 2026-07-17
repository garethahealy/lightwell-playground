#!/usr/bin/env python3
"""Plan phase: inventory direct Maven dependencies from pom.xml (no network).

Usage:
  plan.py [pom.xml]
  plan.py --pom pom.xml -o plan.json

Stdout: JSON inventory of direct deps (excludes Transitive of promotions).
Requires Python 3.14+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lightwell-shared" / "scripts"))

from lightwell_shared.pom_lib import parse_pom  # noqa: E402
from lightwell_shared.schema import stamp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pom_positional",
        nargs="?",
        default="",
        help="Path to pom.xml (default: pom.xml)",
    )
    parser.add_argument("--pom", default="", help="Path to pom.xml")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Write JSON to this path (also prints to stdout)",
    )
    args = parser.parse_args()

    pom_path = Path(args.pom or args.pom_positional or "pom.xml")
    if not pom_path.is_file():
        print(f"error: pom not found: {pom_path}", file=sys.stderr)
        return 2

    pom = parse_pom(pom_path.read_text(encoding="utf-8"))
    inventory = stamp({
        "pom": str(pom_path.resolve()),
        "dependencies": pom["directs"],
        "promotedSkipped": [
            {"ga": p["ga"], "version": p["version"], "via": p["via"]}
            for p in pom["promoted"]
        ],
    })
    text = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
