#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

if len(sys.argv) < 2 or sys.argv[1] not in ("low", "medium", "high"):
    print("Usage: voice_verbosity.py <low|medium|high>")
    print("  low    — Claude summarizes lists; max 2 bullets per response")
    print("  medium — Claude limits lists to 5 items")
    print("  high   — no constraints on format")
    sys.exit(1)

level = sys.argv[1]
config.set_verbosity(level)
print(f"VERBOSITY:{level}")
