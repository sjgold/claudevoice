#!/usr/bin/env python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config
from src.directives import _DIRECTIVES

try:
    cfg = config.load()
    if not cfg.get("enabled", False):
        sys.exit(0)
    level = str(cfg.get("verbosity", "2"))
    directive = _DIRECTIVES.get(level)
    if directive:
        print(json.dumps({
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": directive
            }
        }))
except Exception:
    pass
