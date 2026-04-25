#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

config.set_enabled(True)
cfg = config.load()
verbosity = cfg.get("verbosity", "2")
print(f"Voice is now ON. Verbosity: {verbosity}")
