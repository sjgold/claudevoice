# claude-voice

Gives Claude a voice using your choice of TTS provider — ElevenLabs, OpenAI, or Google Cloud TTS. Works automatically in Claude Code CLI and Claude Desktop on Windows. No system prompts, no manual triggers — turn it on and Claude talks.

Claude Code speaks the full response after it finishes (via a `stop` hook). Claude Desktop speaks sentence-by-sentence as Claude streams, so it feels more like a real conversation. Your provider, voice, and settings persist between sessions in `~/.claude/voice-config.json`.

Code blocks, tool output, and file diffs are filtered out. Only the conversational prose gets spoken.

---

## Providers

| Provider | Free Tier | Voices | Notes |
|---|---|---|---|
| **ElevenLabs** | 10k chars/month | ~30-50 premade via API (10k+ in community library, free-tier API access is premade only) | Best naturalness; great for voice variety |
| **OpenAI** | None | 6 fixed (alloy, echo, nova, onyx, shimmer, fissure) | Cheapest at scale (~$15/1M chars) |
| **Google** | **1M chars/month** | ~12 (en-US Neural2) | Best free tier; excellent quality |

You only need one provider to get started. Set up more later with `/voice provider`.

---

## Requirements

- Python 3.10+
- Windows (desktop daemon uses Windows UIAutomation)
- [ffmpeg](https://ffmpeg.org/download.html) — `winget install ffmpeg`
- API key for at least one provider (see table above)
- Claude Code CLI
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
1. Ask which TTS provider you want to use
2. Prompt for that provider's API key and verify it
3. Let you pick a default voice
4. Write config to `~/.claude/voice-config.json`
5. Register the stop hook in `~/.claude/settings.json`
6. Register the MCP prompt server for Claude Desktop verbosity control

Voice is off by default after setup. Enable it:
```
/voice on
```

---

## Slash Commands

| Command | What it does |
|---|---|
| `/voice on` | Enable TTS |
| `/voice off` | Disable TTS |
| `/voice list` | Show available voices. ElevenLabs defaults to premade voices; use `/voice list all` for everything |
| `/voice pick <name>` | Switch voice — persists between sessions |
| `/voice provider <name>` | Switch provider: `elevenlabs`, `openai`, or `google` |
| `/voice verbosity <level>` | Set verbosity: `low`, `medium`, or `high` |

Examples:
```
/voice provider google
/voice list
/voice pick en-US-Neural2-F
```

---

## Getting API Keys

**ElevenLabs** — [elevenlabs.io](https://elevenlabs.io) → Sign up → Profile → API Keys. Free tier: 10k chars/month.

**OpenAI** — [platform.openai.com](https://platform.openai.com) → API Keys. No free tier; ~$15/1M characters.

**Google Cloud TTS** — [console.cloud.google.com](https://console.cloud.google.com) → Enable "Cloud Text-to-Speech API" → Credentials → Create API Key. Free tier: 1M chars/month (Neural2 voices).

---

## Claude Desktop (sentence streaming)

The desktop daemon runs separately and needs to be started once:

```bash
python daemon/desktop-daemon.py
```

Make sure Claude Desktop is open before starting the daemon. It connects automatically.

To have it start with Windows, add it to Task Scheduler or create a shortcut in your startup folder pointing to:
```
pythonw "C:\path\to\claude-voice\daemon\desktop-daemon.py"
```

The daemon respects the same on/off flag as Claude Code. Use `/voice off` in Claude Code (or flip `enabled` in `~/.claude/voice-config.json`) to silence both at once.

If voice stops working in the desktop daemon, the accessibility tree selector may need updating after a Claude Desktop update. Run the inspector to get a fresh tree dump:
```bash
python daemon/inspect-tree.py > daemon/tree-dump.txt
```
Then look in `tree-dump.txt` for the element containing response text and update `_get_response_text()` in `desktop-daemon.py` accordingly.

---

## Verbosity

Long bullet lists can get exhausting to listen to. Three verbosity levels control how Claude responds — not just how audio is filtered, but how Claude generates its response.

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

Takes effect immediately in the current conversation. No new session needed.

### Verbosity in Claude Desktop

Claude Desktop has no slash commands, but it does have an MCP prompt picker. After running `setup.py` and restarting Claude Desktop, three prompts appear in the prompt picker:

- **Voice: Low verbosity**
- **Voice: Medium verbosity**
- **Voice: High verbosity**

Select one at the start of a conversation and it injects the same directive that `/voice verbosity` would in Claude Code.

---

## Voice Selection

**ElevenLabs**: ElevenLabs has 10,000+ voices in their community library, but only premade official voices (~30-50) are accessible via API on the free tier. `/voice list` shows premade voices by default; `/voice list all` shows everything including any voices you've cloned or created yourself.

```
/voice list          # premade official voices (~30-50)
/voice list all      # everything on your account
/voice pick Rachel
```

**OpenAI**: 6 fixed voices — alloy, echo, nova, onyx, shimmer, fissure. Pick with `/voice pick nova`.

**Google**: `/voice list` shows available en-US Neural2 voices. Pick with `/voice pick en-US-Neural2-F`.

Switch provider at any time:
```
/voice provider openai
/voice list
/voice pick onyx
```

---

## Config

Config lives at `~/.claude/voice-config.json`:

```json
{
  "enabled": false,
  "provider": "google",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "elevenlabs_api_key": "",
  "openai_api_key": "",
  "openai_voice": "nova",
  "openai_model": "tts-1",
  "google_api_key": "AIza...",
  "google_voice": "en-US-Neural2-C",
  "verbosity": "low"
}
```

Only the active provider's key is used. You can store all three and switch freely with `/voice provider`.

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

See the accessibility tree note in the [Claude Desktop](#claude-desktop-sentence-streaming) section above.

**Switching providers doesn't work**

Make sure you've run setup for that provider (or set the API key manually in `~/.claude/voice-config.json`) and run `/voice list` to confirm voices load correctly.

---

## Project Structure

```
claude-voice/
├── src/
│   ├── config.py          # Config read/write (provider, keys, voice)
│   ├── filter.py          # Strips code blocks, tool output, diffs
│   └── tts.py             # Multi-provider TTS (ElevenLabs / OpenAI / Google)
├── hooks/
│   └── stop-hook.py       # Claude Code stop hook
├── daemon/
│   ├── desktop-daemon.py  # Claude Desktop UIAutomation watcher
│   └── inspect-tree.py    # One-time tool to dump accessibility tree
├── commands/              # Python scripts called by slash commands
│   ├── voice_on.py
│   ├── voice_off.py
│   ├── voice_list.py
│   ├── voice_pick.py
│   ├── voice_provider.py
│   └── voice_verbosity.py
├── .claude/commands/voice/  # Slash command markdown files
│   ├── on.md
│   ├── off.md
│   ├── list.md
│   ├── pick.md
│   ├── provider.md
│   └── verbosity.md
├── mcp_server/
│   └── voice-mcp-server.py  # MCP prompts for Claude Desktop verbosity
├── tests/
└── setup.py
```

---

## License

MIT
