#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from src import config

mcp = FastMCP("voice-verbosity")

_DIRECTIVES = {
    "low": (
        "For this conversation: do not use bullet lists. "
        "Summarize any list as a single prose sentence."
    ),
    "medium": (
        "For this conversation: limit bullet lists to 5 items. "
        "If you have more, keep the 5 most important and note how many were omitted."
    ),
    "high": "No special formatting constraints for this conversation.",
}


@mcp.prompt(name="Voice: Low verbosity")
def voice_low() -> str:
    config.set_verbosity("low")
    return _DIRECTIVES["low"]


@mcp.prompt(name="Voice: Medium verbosity")
def voice_medium() -> str:
    config.set_verbosity("medium")
    return _DIRECTIVES["medium"]


@mcp.prompt(name="Voice: High verbosity")
def voice_high() -> str:
    config.set_verbosity("high")
    return _DIRECTIVES["high"]


if __name__ == "__main__":
    mcp.run()
