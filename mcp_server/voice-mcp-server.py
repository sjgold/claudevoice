#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from src import config

mcp = FastMCP("voice-verbosity")

_BASE = (
    "ACTIVE EVERY RESPONSE. No revert after many turns. No filler drift. Still active if unsure.\n\n"
    "Base rules: Drop articles (a/an/the), filler (just/really/basically/actually/simply), "
    "pleasantries (sure/certainly/of course/happy to), hedging. "
    "Short synonyms (big not extensive, fix not 'implement a solution for'). "
    "Technical terms exact. Code blocks unchanged. Errors quoted exact.\n"
    "Pattern: [thing] [action] [reason]. [next step].\n"
    "Auto-clarity: drop caveman for security warnings and irreversible action confirmations. Resume after.\n\n"
)

_DIRECTIVES = {
    "1": (
        _BASE +
        "Level 1 — Caveman ultra: Abbreviate (DB/auth/config/req/res/fn/impl), arrows for causality (X→Y), "
        "one word when one word enough. No bullets — inline as 'X, Y, Z.' Max 2 sentences. "
        "No preamble, no summary, no sign-off."
    ),
    "2": (
        _BASE +
        "Level 2 — Caveman full: Drop articles, fragments OK. "
        "Max 3 bullets; if more, note count ('...and 2 more'). Max 4 sentences. No preamble."
    ),
    "3": (
        _BASE +
        "Level 3 — Caveman lite: Keep full sentences. No filler, no hedging. "
        "Professional but tight. Bullets allowed, no hard limit."
    ),
    "4": "No compression. Respond normally with no constraints on format or length.",
}


@mcp.prompt(name="Voice: Level 1")
def voice_level1() -> str:
    config.set_verbosity("1")
    return _DIRECTIVES["1"]


@mcp.prompt(name="Voice: Level 2")
def voice_level2() -> str:
    config.set_verbosity("2")
    return _DIRECTIVES["2"]


@mcp.prompt(name="Voice: Level 3")
def voice_level3() -> str:
    config.set_verbosity("3")
    return _DIRECTIVES["3"]


@mcp.prompt(name="Voice: Level 4")
def voice_level4() -> str:
    config.set_verbosity("4")
    return _DIRECTIVES["4"]


if __name__ == "__main__":
    mcp.run()
