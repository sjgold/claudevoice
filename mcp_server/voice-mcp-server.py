#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP
from src import config
from src.directives import _DIRECTIVES

mcp = FastMCP("voice-verbosity")


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
