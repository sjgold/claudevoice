# claude-voice

Gives Claude a voice using ElevenLabs TTS. Works automatically in Claude Code CLI and Claude Desktop on Windows — no system prompts, no manual triggers, just turn it on and Claude talks.

Claude Code speaks the full response after it finishes. Claude Desktop speaks sentence-by-sentence as Claude streams, so it feels more like a real conversation.

Code blocks, tool output, and file diffs are filtered out. Only the conversational prose gets spoken.

---

## How it works

**Claude Code** uses a `stop` hook that fires after every response. The hook grabs the last assistant message, strips anything that isn't prose, and sends it to ElevenLabs.

**Claude Desktop** uses a background daemon that watches the app's accessibility tree via Windows UIAutomation. When a new sentence completes and it's not inside a code block, the daemon speaks it immediately.

Both paths share the same ElevenLabs call and filtering logic. Your voice selection persists between sessions in `~/.claude/voice-config.json`.

---

## Requirements

- Python 3.10+
- Windows (the desktop daemon uses Windows UIAutomation)
- [ffmpeg](https://ffmpeg.org/download.html) — install with `winget install ffmpeg` or grab it from the site
- An [ElevenLabs](https://elevenlabs.io) account — free tier works fine
- Claude Code CLI (for the slash commands and stop hook)
- Claude Desktop (optional, for sentence-level streaming)

---

## Setup

```bash
git clone https://github.com/yourusername/claude-voice.git
cd claude-voice
pip install -r requirements.txt
python setup.py
```

Setup will:
1. Ask for your ElevenLabs API key
2. Verify it and show you available voices so you can pick a default
3. Write your config to `~/.claude/voice-config.json`
4. Register the stop hook in `~/.claude/settings.json` (merges into existing hooks, doesn't overwrite anything)

Once setup is done, voice is installed but off by default. Enable it in Claude Code with:

```
/voice on
```

---

## Slash Commands

These work inside any Claude Code session.

| Command | What it does |
|---|---|
| `/voice on` | Enable TTS |
| `/voice off` | Disable TTS |
| `/voice list` | Show all available ElevenLabs voices with their IDs |
| `/voice pick <name>` | Switch to a different voice — persists between sessions |

Example:
```
/voice pick Rachel
```

---

## Claude Desktop (sentence streaming)

The desktop daemon runs separately and needs to be started once:

```bash
python daemon/desktop-daemon.py
```

Make sure Claude Desktop is open before starting the daemon. It'll connect automatically.

To have it start with Windows, add it to Task Scheduler or create a shortcut in your startup folder pointing to:
```
pythonw "C:\path\to\claude-voice\daemon\desktop-daemon.py"
```

The daemon respects the same on/off flag as Claude Code. Use `/voice off` in Claude Code (or flip `enabled` in `~/.claude/voice-config.json`) to silence both surfaces at once.

---

## Verbosity

Long bullet lists can get exhausting to listen to. Voice has three verbosity levels that control how Claude responds — not just how the audio is filtered, but how Claude actually generates its response.

```
/voice verbosity low
/voice verbosity medium
/voice verbosity high
```

| Level | Behavior |
|---|---|
| `low` (default) | Claude summarizes lists in prose. Max 2 bullet points spoken. |
| `medium` | Claude limits lists to 5 items and summarizes the rest. |
| `high` | No constraints — Claude responds however it wants. |

This works in two layers. The slash command (Claude Code) or prompt picker (Claude Desktop) tells Claude directly — in the current conversation — to respond more concisely. No new session needed, takes effect immediately. A post-processing fallback catches anything that slips through.

Your CLAUDE.md is never touched automatically. If you want verbosity to persist across all sessions, add the instruction to your own CLAUDE.md manually.

### Verbosity in Claude Desktop

Claude Desktop has no slash commands, but it does have an MCP prompt picker. After running `setup.py` and restarting Claude Desktop, three prompts appear in the prompt picker:

- **Voice: Low verbosity**
- **Voice: Medium verbosity**
- **Voice: High verbosity**

Select one at the start of a conversation and it injects the same directive that `/voice verbosity` would in Claude Code. The setting is also saved to config so the TTS filter stays in sync.

---

## Voice selection

Run `/voice list` to see what's available on your ElevenLabs account. Then:

```
/voice pick Adam
```

Your selection is saved immediately and survives restarts. The desktop daemon picks it up on the next response without needing a restart.

---

## Troubleshooting

**No audio at all**

Check that ffplay is on your PATH:
```bash
ffplay -version
```
If not found, install ffmpeg and make sure it's in your PATH.

**Claude Code not speaking**

Check that the hook registered correctly:
```bash
python -c "import json; d=json.load(open('C:/Users/<you>/.claude/settings.json')); print(d.get('hooks', {}))"
```
You should see a `Stop` entry pointing to `stop-hook.py`. If it's missing, run `setup.py` again.

**Desktop daemon not finding Claude**

The daemon looks for a window with "Claude" in the title. Make sure Claude Desktop is open and visible (not minimized) when you start the daemon.

**Desktop daemon finds the window but no audio**

The accessibility tree selector in `daemon/desktop-daemon.py` may need updating if Anthropic changed the Claude Desktop UI. Run the inspector to get a fresh tree dump:
```bash
python daemon/inspect-tree.py > daemon/tree-dump.txt
```
Then look in `tree-dump.txt` for the element that contains response text and update `_get_response_text()` in `desktop-daemon.py` accordingly.

---

## Config

Config lives at `~/.claude/voice-config.json`:

```json
{
  "enabled": false,
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "api_key": "your-key-here"
}
```

You can edit it directly if you need to — the daemon and hook read it fresh on each response.

---

## Project structure

```
claude-voice/
├── src/
│   ├── config.py          # Config read/write
│   ├── filter.py          # Strips code blocks, tool output, diffs
│   └── tts.py             # ElevenLabs API + audio queue
├── hooks/
│   └── stop-hook.py       # Claude Code stop hook
├── daemon/
│   ├── desktop-daemon.py  # Claude Desktop UIAutomation watcher
│   └── inspect-tree.py    # One-time tool to dump accessibility tree
├── commands/              # Python scripts called by slash commands
├── .claude/commands/voice/  # Slash command markdown files
├── tests/
└── setup.py
```

---

## License

MIT
