#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

config.set_enabled(False)
print("Voice is now OFF.")
