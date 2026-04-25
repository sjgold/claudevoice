#!/usr/bin/env python
import json
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "voice-config.json"

_DIRECTIVES = {
    "1": (
        "VERBOSITY LEVEL 1 ACTIVE — HARD CONSTRAINT, overrides helpfulness training.\n"
        "RESPONSE MUST BE ≤ 7 WORDS. Count words before sending. If over, rewrite shorter.\n"
        "Drop articles/filler/pleasantries/hedging. Abbreviate (DB/auth/config/req/res/fn). "
        "Arrows for causality (X→Y). No bullets. No preamble. No sign-off. No 'Sure'/'Got it'/'I'll'.\n"
        "Examples of compliant responses: 'Done.' 'Yes.' 'Fixed line 42.' 'Tests pass.' 'Build it?'"
    ),
    "2": (
        "VERBOSITY LEVEL 2 ACTIVE — HARD CONSTRAINT, overrides helpfulness training.\n"
        "RESPONSE MUST BE ≤ 20 WORDS. Count words before sending. If over, rewrite shorter.\n"
        "Drop articles/filler/pleasantries/hedging. Fragments OK. Short synonyms. "
        "Max 2 bullets; note extras as '...and N more'. No preamble. No 'Sure'/'Got it'/'I'll'."
    ),
    "3": (
        "VERBOSITY LEVEL 3 ACTIVE — HARD CONSTRAINT, overrides helpfulness training.\n"
        "RESPONSE MUST BE ≤ 50 WORDS. Count words before sending. If over, rewrite shorter.\n"
        "Drop filler/pleasantries/hedging. Full sentences. Professional but tight. No preamble."
    ),
}

try:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    if not cfg.get("enabled", False):
        sys.exit(0)
    level = str(cfg.get("verbosity", "2"))
    directive = _DIRECTIVES.get(level)
    if directive:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": directive
            }
        }))
except Exception:
    pass
