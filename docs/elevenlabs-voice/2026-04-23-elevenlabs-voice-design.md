# ElevenLabs Voice — Design Spec
**Date:** 2026-04-23  
**Status:** Approved

---

## Overview

A personal voice system that makes Claude speak its responses aloud using ElevenLabs TTS. Works automatically on two surfaces: Claude Code CLI (via stop hook) and Claude Desktop (via UIAutomation daemon). No system prompts, no Claude tool calls required — both paths fire without any user or model action beyond toggling the feature on.

---

## Goals

- Claude speaks filtered conversational text automatically after every response
- Works in Claude Code CLI and Claude Desktop
- Easily toggled on/off via slash commands in Claude Code
- User can list and select ElevenLabs voices from within Claude Code
- Code blocks, tool call output, file diffs, and inline code are never spoken

---

## Architecture

### Shared Voice Engine (`src/`)

Three Python modules shared by both integration paths:

**`filter.py`** — Text filtering  
Takes a raw Claude response string and verbosity level. Strips: triple-backtick code fences and their contents, inline backtick code, tool call/result blocks (identified by Claude Code's XML-like markers), file diff blocks. Applies verbosity rules to bullet and numbered lists (lines starting with `-`, `*`, or `N.`). Returns only clean prose. A sentence is kept only if it contains meaningful words (not just punctuation or whitespace).

**`tts.py`** — ElevenLabs TTS + audio playback  
Accepts a string (either full response or a single sentence). Calls the ElevenLabs `/v1/text-to-speech/{voice_id}` endpoint with streaming enabled. Plays the returned MP3 via `ffplay` (bundled with ffmpeg). Maintains a thread-safe audio queue so sentence-level calls don't overlap. Respects the `enabled` flag in config before making any API call.

**`config.py`** — Config read/write  
Reads and writes `~/.claude/voice-config.json`. Schema:
```json
{
  "enabled": true,
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "api_key": "sk-...",
  "verbosity": "low"
}
```

`verbosity` controls response style at two levels:

**Primary — in-conversation directive (injected by the `/voice verbosity` slash command):**  
The slash command markdown file instructs Claude to run the config script AND adopt the verbosity rule immediately in the current conversation — no new session needed. Claude generates concise responses natively from that point forward.

| Level | In-conversation instruction to Claude |
|---|---|
| `"low"` | Summarize lists of 3+ items in 1–2 sentences. Max 2 bullet points per response. Note how many items were condensed. |
| `"medium"` | Limit bullet lists to 5 items. Summarize anything beyond that. |
| `"high"` | No special constraints on format or length. |

**Fallback — post-processing filter (`filter.py`):**  
Still truncates lists in the text before TTS as a safety net, using the same limits. Catches cases where Claude doesn't follow the directive, and handles Claude Desktop (which doesn't go through the slash command system).

`~/.claude/CLAUDE.md` is never written to automatically. Users who want verbosity to persist across all sessions can add the instruction to their own CLAUDE.md manually.

---

## Integration 1: Claude Code (stop hook)

**Trigger:** Claude Code's `stop` hook fires after Claude finishes every response.

**Hook script:** `hooks/stop-hook.py`  
Reads the full response text from stdin (Claude Code passes the conversation JSON to the hook). Extracts the last assistant message. Passes it to `filter.py`, then `tts.py`. Exits silently if voice is disabled or the filtered text is empty.

**Registration:** `setup.py` merges the hook entry into `~/.claude/settings.json` under `hooks.Stop`, preserving any existing hooks. The command path is the absolute path to `hooks/stop-hook.py` resolved at setup time:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "python C:/Users/SJG/Documents/CodePlayground/claude voice/hooks/stop-hook.py" }]
      }
    ]
  }
}
```

---

## Integration 2: Claude Desktop (UIAutomation daemon)

**Trigger:** Python daemon using Windows `UIAutomation` library watches the Claude Desktop window's accessibility tree for new streamed text.

**Daemon:** `daemon/desktop-daemon.py`  
- Locates the Claude Desktop window by process name (`Claude.exe`)
- Polls the accessibility tree every 100ms for the most recent assistant message container
- Buffers incoming text as Claude streams it
- When a sentence boundary is detected (`.`, `?`, `!` followed by whitespace or end of stream) AND the buffered text is not inside a code fence, passes the sentence to `filter.py` then `tts.py`
- Resets sentence buffer when a new assistant turn begins
- Checks `config.py` enabled flag on each sentence — toggling off mid-response stops speech immediately
- Started/stopped alongside the voice system; runs as a background process

**Sentence boundary logic:** A sentence is considered complete when:
1. A terminal punctuation character is followed by a space or the stream pauses >300ms
2. The running buffer does not contain an unclosed triple-backtick
3. The sentence has at least 4 words

---

## Integration 3: MCP Prompt Server (Claude Desktop verbosity)

**Problem:** Claude Desktop has no slash commands, so `/voice verbosity` can't inject the verbosity directive there.

**Solution:** A local MCP server exposes named prompts that appear in Claude Desktop's prompt picker UI. The user selects one, it injects the directive into the conversation immediately — same effect as the slash command in Claude Code.

**Server:** `mcp_server/voice-mcp-server.py`  
Runs as a stdio MCP server using the `mcp` Python SDK. Exposes three prompts:

| Prompt name | Label in Claude Desktop | Behavior |
|---|---|---|
| `voice-verbosity-low` | Voice: Low verbosity | Injects low directive, writes `verbosity: low` to config |
| `voice-verbosity-medium` | Voice: Medium verbosity | Injects medium directive, writes `verbosity: medium` to config |
| `voice-verbosity-high` | Voice: High verbosity | Injects high directive, writes `verbosity: high` to config |

Each prompt returns a `user` message containing the verbosity instruction text. Claude Desktop injects it into the conversation as if the user typed it.

**Registration:** `setup.py` merges the server entry into `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "claude-voice": {
      "command": "python",
      "args": ["C:/Users/SJG/Documents/CodePlayground/claude voice/mcp_server/voice-mcp-server.py"]
    }
  }
}
```
Claude Desktop must be restarted once after registration for the prompts to appear.

---

## Slash Commands (Claude Code)

Custom commands in `.claude/commands/voice/`. Each is a markdown file with `$ARGUMENTS` where needed.

| Command | File | Behavior |
|---|---|---|
| `/voice on` | `voice-on.md` | Sets `enabled: true` in config. Confirms to user. |
| `/voice off` | `voice-off.md` | Sets `enabled: false` in config. Confirms to user. |
| `/voice list` | `voice-list.md` | Calls ElevenLabs `/v1/voices`, prints name + ID table. |
| `/voice pick` | `voice-pick.md` | Takes voice name or ID as `$ARGUMENTS`, writes `voice_id` to config. Confirms selection. |
| `/voice verbosity` | `voice-verbosity.md` | Takes `low`, `medium`, or `high` as `$ARGUMENTS`. Writes `verbosity` to config, then instructs Claude to follow the verbosity rule immediately in the current conversation. Takes effect instantly — no new session needed. |

Commands are shell-executed via Claude — they run a small Python script that updates config and print a confirmation message back into the conversation.

---

## Setup Flow (first run)

1. User gets ElevenLabs API key from elevenlabs.io
2. Runs `python setup.py` — prompts for API key, calls `/v1/voices` to verify, writes config
3. Installs ffmpeg if not present (setup.py checks and prints instructions)
4. Hook is registered in `~/.claude/settings.json` by setup.py
5. Desktop daemon started via `python daemon/desktop-daemon.py` (user adds to Windows startup if desired)
6. User runs `/voice on` in Claude Code to enable

---

## File Structure

```
claude voice/
├── src/
│   ├── filter.py          # Text filtering logic
│   ├── tts.py             # ElevenLabs API + audio playback
│   └── config.py          # Config read/write
├── hooks/
│   └── stop-hook.py       # Claude Code stop hook entry point
├── daemon/
│   └── desktop-daemon.py  # Claude Desktop UIAutomation watcher
├── commands/              # Slash command scripts (called by .claude/commands/)
│   ├── voice_on.py
│   ├── voice_off.py
│   ├── voice_list.py
│   └── voice_pick.py
├── .claude/
│   └── commands/
│       └── voice/
│           ├── on.md
│           ├── off.md
│           ├── list.md
│           └── pick.md
├── mcp_server/
│   └── voice-mcp-server.py  # MCP prompt server for Claude Desktop verbosity
├── setup.py               # First-run setup
└── requirements.txt       # pywinauto, requests, mcp, etc.
```

---

## Dependencies

- **Python 3.10+**
- `requests` — ElevenLabs API calls
- `pywinauto` — Windows UIAutomation for desktop daemon
- `mcp>=1.0.0` — MCP Python SDK for the Claude Desktop prompt server
- `ffmpeg` / `ffplay` — MP3 playback (user installs separately; setup.py checks)
- ElevenLabs account (free tier sufficient for personal use)

---

## Out of Scope

- Claude.ai web support (no hook or accessibility path without a browser extension)
- Multi-speaker voices or emotion control
- Local TTS fallback if ElevenLabs is unreachable
- Conversation history / replay
