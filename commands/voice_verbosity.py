#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

if len(sys.argv) < 2 or sys.argv[1] not in ("1", "2", "3", "4"):
    print("Usage: voice_verbosity.py <1|2|3|4>")
    print("  1 — ultra compressed (caveman ultra)")
    print("  2 — compressed (caveman full)")
    print("  3 — tight (caveman lite)")
    print("  4 — no constraints")
    sys.exit(1)

level = sys.argv[1]
config.set_verbosity(level)
print(f"VERBOSITY:{level}")
