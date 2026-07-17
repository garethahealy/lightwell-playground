"""Ensure ``scripts/`` is on sys.path so ``lightwell_shared`` imports resolve."""

from __future__ import annotations

import sys
from pathlib import Path

# Package lives at scripts/lightwell_shared/; parent must be on sys.path.
_SCRIPTS = Path(__file__).resolve().parents[1]


def ensure_scripts_path() -> Path:
    root = str(_SCRIPTS)
    if root not in sys.path:
        sys.path.insert(0, root)
    return _SCRIPTS
