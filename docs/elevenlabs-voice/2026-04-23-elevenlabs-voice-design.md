# Claude Voice — Multi-Provider TTS — Design Spec
**Date:** 2026-04-23  
**Status:** Approved — Updated 2026-04-23 (added OpenAI TTS provider, added Google Cloud TTS provider)

---

## Overview

A personal voice system that makes Claude speak its responses aloud using either ElevenLabs or OpenAI TTS. Works automatically on two surfaces: Claude Code CLI (via stop hook) and Claude Desktop (via UIAutomation daemon). No system prompts, no Claude tool calls required — both paths fire without any user or model action beyond toggling the feature on. The active TTS provider is configurable and switchable at any time.

---

## Goals

- Claude speaks filtered conversational text automatically after every response
- Works in Claude Code CLI and Claude Desktop
- Easily toggled on/off via slash commands in Claude Code
- User can list and select ElevenLabs premade voices (default) or all voices from within Claude Code
- User can switch between ElevenLabs, OpenAI, and Google TTS providers
- Code blocks, tool call output, file diffs, and inline code are never spoken

---

## Architecture

### Shared Voice Engine (`src/`)

Three Python modules shared by both integration paths:

**`filter.py`** — Text filtering  
Takes a raw Claude response string and verbosity level. Strips: triple-backtick code fences and their contents, inline backtick code, tool call/result blocks (identified by Claude Code's XML-like markers), file diff blocks. Applies verbosity rules to bullet and numbered lists (lines starting with `-`, `*`, or `N.`). Returns only clean prose. A sentence is kept only if it contains meaningful words (not just punctuation or whitespace).

**`tts.py`** — Multi-provider TTS + audio playback  
Accepts a string (either full response or a single sentence). Routes to ElevenLabs, OpenAI, or Google based on the `provider` field in config. For ElevenLabs: calls `/v1/text-to-speech/{voice_id}` with streaming enabled. For OpenAI: calls `POST /v1/audio/speech` (no streaming — returns a full audio blob) using models `tts-1` or `tts-1-hd` and one of 6 voices: `alloy`, `echo`, `nova`, `onyx`, `shimmer`, `fissure`. For Google: calls `POST https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}` with request body `{"input": {"text": "..."}, "voice": {"languageCode": "en-US", "name": "en-US-Neural2-C"}, "audioConfig": {"audioEncoding": "MP3"}}`; auth is via API key in the query param (not a header); response audio is base64-encoded in `response.json()["audioContent"]` and must be decoded before playback; no streaming — full audio blob. English Neural2 voices only in v1. Plays the returned MP3 via `ffplay` (bundled with ffmpeg). Maintains a thread-safe audio queue so sentence-level calls don't overlap. Respects the `enabled` flag in config before making any API call.

**`config.py`** — Config read/write  
Reads and writes `~/.claude/voice-config.json`. Schema:
```json
{
  "enabled": true,
  "provider": "elevenlabs",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "elevenlabs_api_key": "sk-...",
  "openai_api_key": "sk-...",
  "openai_voice": "nova",
  "openai_model": "tts-1",
  "google_api_key": "AIza...",
  "google_voice": "en-US-Neural2-C",
  "verbosity": "low"
}
```

`provider` is `"elevenlabs"`, `"openai"`, or `"google"`. Only the active provider's API key is required — the others may be left empty. The old `api_key` field is replaced by `elevenlabs_api_key`.

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
| `/voice list` | `voice-list.md` | Lists ElevenLabs premade voices by default (`category=premade`, ~30-50 voices). `/voice list all` shows all voices including user-created clones. OpenAI and Google always show full list (6 and ~12 voices respectively). |
| `/voice pick` | `voice-pick.md` | Takes voice name or ID as `$ARGUMENTS`, writes `voice_id` to config. Confirms selection. |
| `/voice verbosity` | `voice-verbosity.md` | Takes `low`, `medium`, or `high` as `$ARGUMENTS`. Writes `verbosity` to config, then instructs Claude to follow the verbosity rule immediately in the current conversation. Takes effect instantly — no new session needed. |
| `/voice provider` | `voice-provider.md` | Takes `elevenlabs`, `openai`, or `google` as `$ARGUMENTS`, writes `provider` to config. Confirms switch. |

Commands are shell-executed via Claude — they run a small Python script that updates config and print a confirmation message back into the conversation.

> **Note — ElevenLabs Voice Library vs. API voices:**  
> ElevenLabs hosts 10,000+ community voices in their Voice Library, but the Voice Library is **not accessible via API on the free tier**. The `/v1/voices` endpoint returns only the user's own voices (created or cloned) plus ElevenLabs' official premade voices. Filtering by `category=premade` returns only the official ElevenLabs voices (~30-50), which is the sensible default for `/voice list`. Users who have created or cloned their own voices can run `/voice list all` to see everything the API returns.

---

## Setup Flow (first run)

1. Runs `python setup.py` — asks user which provider they want (ElevenLabs, OpenAI, or Google)
2. Prompts for the API key of the chosen provider (offers to set others if desired)
3. Verifies the key against the chosen provider's API:
   - ElevenLabs: calls `/v1/voices` to verify key and lets user pick a voice from the returned list
   - OpenAI: makes a small test TTS call (or calls `/v1/models`) to verify key; lets user pick from the 6 fixed voices (`alloy`, `echo`, `nova`, `onyx`, `shimmer`, `fissure`)
   - Google: calls the voices list endpoint filtered to `en-US` Neural2 voices to verify key; lets user pick from those voices. Free tier: 1M chars/month.
4. Writes config with `provider`, the verified key(s), and selected voice
5. Installs ffmpeg if not present (setup.py checks and prints instructions)
6. Hook is registered in `~/.claude/settings.json` by setup.py
7. Desktop daemon started via `python daemon/desktop-daemon.py` (user adds to Windows startup if desired)
8. User runs `/voice on` in Claude Code to enable

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
│   ├── voice_pick.py
│   └── voice_provider.py
├── .claude/
│   └── commands/
│       └── voice/
│           ├── on.md
│           ├── off.md
│           ├── list.md
│           ├── pick.md
│           └── provider.md
├── mcp_server/
│   └── voice-mcp-server.py  # MCP prompt server for Claude Desktop verbosity
├── setup.py               # First-run setup
└── requirements.txt       # pywinauto, requests, mcp, etc.
```

---

## Dependencies

- **Python 3.10+**
- `requests` — API calls for ElevenLabs, OpenAI, and Google (no extra packages needed for any provider)
- `pywinauto` — Windows UIAutomation for desktop daemon
- `mcp>=1.0.0` — MCP Python SDK for the Claude Desktop prompt server
- `ffmpeg` / `ffplay` — MP3 playback (user installs separately; setup.py checks)
- ElevenLabs account (free tier sufficient for personal use) — only required if using ElevenLabs provider
- OpenAI account — only required if using OpenAI provider
- Google Cloud account with Text-to-Speech API enabled — only required if using Google provider. Note: Google returns audio as a base64-encoded string in `audioContent`; `tts.py` decodes it before passing to `ffplay`.

---

## Provider Comparison

| Provider | Free Tier | Voices | Quality | Notes |
|---|---|---|---|---|
| ElevenLabs | 10k chars/month | ~100, named | Excellent | Best naturalness, voice cloning |
| OpenAI | None | 6 fixed | Good | Cheapest at scale ($15/1M chars) |
| Google | 1M chars/month | ~12 (en-US Neural2) | Good | Best free tier; base64 response |

---

## Out of Scope

- Claude.ai web support (no hook or accessibility path without a browser extension)
- Multi-speaker voices or emotion control
- Conversation history / replay
