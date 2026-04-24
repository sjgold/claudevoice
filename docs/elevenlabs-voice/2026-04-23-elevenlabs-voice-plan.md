# ElevenLabs Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Review pipeline per task (4 stages):**
> 1. **Codex** (`codex:codex-rescue`) — implements the task, writes code, runs tests, commits
> 2. **Claude Haiku** — spec compliance review: does the implementation match the spec exactly? No more, no less.
> 3. **Claude Sonnet** — code quality review: is it well-structured, tested, and maintainable?
> 4. **Codex adversarial** (`codex-companion.mjs adversarial-review`) — tries to break it: finds edge cases, logic bugs, missing error handling
>
> **Model assignment:**
> - Tasks 1–7 (scaffold, config, filter, tts, stop-hook, slash commands, markdown): Codex implements, Haiku reviews spec, Sonnet reviews quality, Codex adversarial
> - Tasks 8–10 (tree discovery, desktop daemon, setup.py): Codex implements with Sonnet spec+quality reviewers, Codex adversarial
> - Task 11 (integration): manual with Sonnet oversight

**Goal:** Build a personal voice system that automatically speaks Claude's filtered conversational responses via ElevenLabs TTS, working in both Claude Code CLI (stop hook) and Claude Desktop (UIAutomation daemon).

**Architecture:** A shared Python voice engine (`src/`) handles filtering, TTS, and config persistence. Claude Code fires the engine via a `stop` hook on every response. Claude Desktop fires it via a background daemon that watches the accessibility tree for new streamed text and speaks sentence-by-sentence.

**Tech Stack:** Python 3.10+, `requests` (ElevenLabs API), `pywinauto` (Windows UIAutomation), `ffplay` (MP3 playback via ffmpeg), `pytest` (tests), Claude Code hooks + custom slash commands.

---

## File Map

| File | Responsibility |
|---|---|
| `src/__init__.py` | Package marker |
| `src/config.py` | Read/write `~/.claude/voice-config.json`; single source of truth for enabled flag, voice ID, API key |
| `src/filter.py` | Strip code fences, inline code, tool blocks, diffs from response text |
| `src/tts.py` | ElevenLabs API call + ffplay audio queue |
| `hooks/stop-hook.py` | Claude Code Stop hook entry point; reads stdin JSON, extracts last assistant text, calls filter+tts |
| `daemon/desktop-daemon.py` | Windows UIAutomation watcher; polls Claude Desktop accessibility tree, buffers sentences, calls filter+tts |
| `daemon/inspect-tree.py` | One-time utility to dump Claude Desktop's accessibility tree so we can find the right element selectors |
| `commands/voice_on.py` | Set enabled=true in config, print confirmation |
| `commands/voice_off.py` | Set enabled=false in config, print confirmation |
| `commands/voice_list.py` | Fetch ElevenLabs voice list, print formatted table |
| `commands/voice_pick.py` | Accept voice name/ID arg, write to config, confirm — voice persists in JSON across restarts |
| `commands/voice_provider.py` | Accept provider arg (elevenlabs|openai), write to config, confirm |
| `.claude/commands/voice/on.md` | Slash command: `/voice on` |
| `.claude/commands/voice/off.md` | Slash command: `/voice off` |
| `.claude/commands/voice/list.md` | Slash command: `/voice list` |
| `.claude/commands/voice/pick.md` | Slash command: `/voice pick <name>` |
| `.claude/commands/voice/provider.md` | Slash command: `/voice provider <elevenlabs\|openai>` |
| `setup.py` | First-run: prompt API key, verify, write config, check ffmpeg, register stop hook in settings.json |
| `requirements.txt` | Python dependencies |
| `tests/test_config.py` | Tests for config.py |
| `tests/test_filter.py` | Tests for filter.py |
| `tests/test_tts.py` | Tests for tts.py (mocked API) |
| `tests/test_stop_hook.py` | Tests for stop-hook.py stdin parsing |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `hooks/__init__.py`
- Create: `commands/__init__.py`
- Create: `daemon/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.31.0
pywinauto>=0.6.8
mcp>=1.0.0
pytest>=7.4.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create package markers**

```bash
touch "src/__init__.py" "tests/__init__.py" "hooks/__init__.py" "commands/__init__.py" "daemon/__init__.py"
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error. If `pywinauto` fails, ensure you're on Windows with Python 3.10+.

- [ ] **Step 4: Verify pytest works**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/ -v
```

Expected: `no tests ran` (0 collected) — that's correct, no tests yet.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && git init && git add requirements.txt src/__init__.py tests/__init__.py hooks/__init__.py commands/__init__.py daemon/__init__.py && git commit -m "feat: project scaffold"
```

---

## Task 2: config.py

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

Config reads/writes `~/.claude/voice-config.json`. Voice ID persists across restarts — selecting voice B and restarting always resumes as voice B.

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_returns_defaults_when_no_file(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["enabled"] is False
    assert cfg["voice_id"] == "21m00Tcm4TlvDq8ikWAM"
    assert cfg["elevenlabs_api_key"] == ""


def test_save_and_load_roundtrip(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.save({"enabled": True, "voice_id": "abc123", "elevenlabs_api_key": "sk-test"})
        cfg = config.load()
    assert cfg["enabled"] is True
    assert cfg["voice_id"] == "abc123"
    assert cfg["elevenlabs_api_key"] == "sk-test"


def test_set_enabled_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_enabled(True)
        assert config.is_enabled() is True
        config.set_enabled(False)
        assert config.is_enabled() is False


def test_verbosity_defaults_to_low(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["verbosity"] == "low"


def test_set_verbosity_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_verbosity("medium")
        cfg = config.load()
    assert cfg["verbosity"] == "medium"


def test_set_voice_persists_across_reload(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_voice("voice-xyz-789")
        cfg = config.load()
    assert cfg["voice_id"] == "voice-xyz-789"


def test_load_merges_missing_keys(tmp_path):
    config_path = tmp_path / "voice-config.json"
    config_path.write_text(json.dumps({"api_key": "sk-existing"}))
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["api_key"] == "sk-existing"
    assert cfg["enabled"] is False  # default applied for missing key
    assert cfg["voice_id"] == "21m00Tcm4TlvDq8ikWAM"


def test_provider_defaults_to_elevenlabs(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["provider"] == "elevenlabs"

def test_set_provider_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_provider("openai")
        assert config.get_provider() == "openai"

def test_google_defaults_present(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["google_api_key"] == ""
    assert cfg["google_voice"] == "en-US-Neural2-C"

def test_set_provider_accepts_google(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_provider("google")
        assert config.get_provider() == "google"

def test_set_provider_rejects_invalid(tmp_path):
    # Update existing test — google is now valid, keep testing a bad value
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        with pytest.raises(ValueError):
            config.set_provider("amazon")

def test_load_merges_missing_keys_with_openai_defaults(tmp_path):
    config_path = tmp_path / "voice-config.json"
    config_path.write_text(json.dumps({"elevenlabs_api_key": "sk-existing"}))
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["elevenlabs_api_key"] == "sk-existing"
    assert cfg["openai_api_key"] == ""
    assert cfg["openai_voice"] == "nova"
    assert cfg["openai_model"] == "tts-1"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement src/config.py**

```python
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "voice-config.json"

_DEFAULTS = {
    "enabled": False,
    "provider": "elevenlabs",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "elevenlabs_api_key": "",
    "openai_api_key": "",
    "openai_voice": "nova",
    "openai_model": "tts-1",
    "google_api_key": "",
    "google_voice": "en-US-Neural2-C",
    "verbosity": "low",
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return _DEFAULTS.copy()
    with open(CONFIG_PATH) as f:
        return {**_DEFAULTS, **json.load(f)}


def save(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def set_enabled(value: bool) -> None:
    cfg = load()
    cfg["enabled"] = value
    save(cfg)


def set_voice(voice_id: str) -> None:
    cfg = load()
    cfg["voice_id"] = voice_id
    save(cfg)


def set_verbosity(level: str) -> None:
    if level not in ("low", "medium", "high"):
        raise ValueError(f"Invalid verbosity: {level!r}. Use low, medium, or high.")
    cfg = load()
    cfg["verbosity"] = level
    save(cfg)


def set_provider(provider: str) -> None:
    if provider not in ("elevenlabs", "openai", "google"):
        raise ValueError(f"Invalid provider: {provider!r}. Use elevenlabs, openai, or google.")
    cfg = load()
    cfg["provider"] = provider
    save(cfg)


def get_provider() -> str:
    return load()["provider"]


def is_enabled() -> bool:
    return load()["enabled"]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_config.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py && git commit -m "feat: config read/write with persistent voice selection"
```

---

## Task 3: filter.py

**Files:**
- Create: `src/filter.py`
- Create: `tests/test_filter.py`

Strips code fences, inline code, tool blocks, and file diffs. Returns clean prose. This is the most critical module — a bug here either silences good content or speaks noise.

- [ ] **Step 1: Write failing tests**

Create `tests/test_filter.py`:

```python
from src.filter import filter_response, extract_prose_sentences


def test_strips_triple_backtick_fence():
    text = "Here is the answer.\n```python\nprint('hello')\n```\nThat is the code."
    result = filter_response(text)
    assert "print" not in result
    assert "Here is the answer." in result
    assert "That is the code." in result


def test_strips_inline_code():
    text = "Use the `ffplay` command to play audio files."
    result = filter_response(text)
    assert "`ffplay`" not in result
    assert "Use the" in result
    assert "command to play audio files." in result


def test_strips_tool_call_blocks():
    text = "Let me check that.\n<tool_use>\n{\"name\": \"bash\"}\n</tool_use>\nDone checking."
    result = filter_response(text)
    assert "tool_use" not in result
    assert "Let me check that." in result
    assert "Done checking." in result


def test_strips_diff_blocks():
    text = "I made a change.\n```diff\n- old line\n+ new line\n```\nAll done."
    result = filter_response(text)
    assert "- old line" not in result
    assert "I made a change." in result
    assert "All done." in result


def test_pure_code_response_returns_empty():
    text = "```python\ndef foo():\n    return 42\n```"
    result = filter_response(text)
    assert result.strip() == ""


def test_plain_prose_passes_through():
    text = "That is a great question. The answer depends on context."
    result = filter_response(text)
    assert "That is a great question." in result
    assert "The answer depends on context." in result


def test_extract_sentences_filters_short():
    text = "Yes. That is an interesting approach to the problem. No. Absolutely."
    sentences = extract_prose_sentences(text)
    # "Yes." and "No." and "Absolutely." are too short (< 4 words)
    assert all(len(s.split()) >= 4 for s in sentences)


def test_extract_sentences_handles_question_and_exclamation():
    text = "Is this the right approach? It definitely seems correct! Let me explain why."
    sentences = extract_prose_sentences(text)
    assert len(sentences) == 3


def test_low_verbosity_summarizes_lists():
    text = "Here are the steps:\n- First do this\n- Then do that\n- Also this\n- And this too\n- Finally this"
    result = filter_response(text, verbosity="low")
    assert "The response included a list of 5 items" in result
    assert "First do this" not in result


def test_medium_verbosity_keeps_three_bullets():
    items = "\n".join(f"- Item {i}" for i in range(1, 6))
    text = f"The list:\n{items}"
    result = filter_response(text, verbosity="medium")
    assert "Item 1" in result
    assert "Item 2" in result
    assert "Item 3" in result
    assert "Item 4" not in result
    assert "2 more" in result


def test_high_verbosity_reads_all_bullets():
    items = "\n".join(f"- Item {i}" for i in range(1, 9))
    text = f"Full list:\n{items}"
    result = filter_response(text, verbosity="high")
    assert "Item 8" in result


def test_markdown_headers_stripped():
    text = "## Architecture\n\nThis is the main explanation of the architecture."
    result = filter_response(text)
    assert "##" not in result
    assert "This is the main explanation" in result


def test_strips_horizontal_rules():
    text = "First point.\n\n---\n\nSecond point here."
    result = filter_response(text)
    assert "---" not in result
    assert "First point." in result
    assert "Second point here." in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_filter.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.filter'`

- [ ] **Step 3: Implement src/filter.py**

```python
import re

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_TOOL_BLOCK = re.compile(r"<tool_(?:use|result)>[\s\S]*?</tool_(?:use|result)>", re.DOTALL)
_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_HORIZONTAL_RULE = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)
_LIST_ITEM = re.compile(r"^(\s*(?:[-*]|\d+\.)\s+.+)$", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _apply_verbosity(text: str, verbosity: str) -> str:
    if verbosity == "high":
        return text

    lines = text.splitlines(keepends=True)
    result = []
    list_items = []
    in_list = False

    def flush_list():
        if not list_items:
            return
        if verbosity == "low":
            result.append(f"The response included a list of {len(list_items)} items.\n")
        elif verbosity == "medium":
            kept = list_items[:3]
            remaining = len(list_items) - 3
            result.extend(kept)
            if remaining > 0:
                result.append(f"  ...and {remaining} more.\n")

    for line in lines:
        if _LIST_ITEM.match(line):
            in_list = True
            list_items.append(line)
        else:
            if in_list:
                flush_list()
                list_items = []
                in_list = False
            result.append(line)

    if in_list:
        flush_list()

    return "".join(result)


def filter_response(text: str, verbosity: str = "low") -> str:
    text = _CODE_FENCE.sub("", text)
    text = _TOOL_BLOCK.sub("", text)
    text = _INLINE_CODE.sub("", text)
    text = _MARKDOWN_HEADER.sub("", text)
    text = _HORIZONTAL_RULE.sub("", text)
    text = _apply_verbosity(text, verbosity)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_prose_sentences(text: str, verbosity: str = "low") -> list[str]:
    filtered = filter_response(text, verbosity=verbosity)
    parts = _SENTENCE_SPLIT.split(filtered)
    return [s.strip() for s in parts if len(s.split()) >= 4]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_filter.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/filter.py tests/test_filter.py && git commit -m "feat: text filter strips code, tools, diffs from Claude responses"
```

---

## Task 4: tts.py

**Files:**
- Create: `src/tts.py`
- Create: `tests/test_tts.py`

Calls ElevenLabs or OpenAI TTS API (depending on configured provider) and plays MP3 via ffplay. A thread-safe audio queue ensures sentences don't overlap when called rapidly from the desktop daemon.

- [ ] **Step 1: Write failing tests**

Create `tests/test_tts.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, call
from src import tts


def test_speak_does_nothing_when_disabled(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": False, "provider": "elevenlabs", "voice_id": "abc",
        "elevenlabs_api_key": "sk-test", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_post = mocker.patch("src.tts.requests.post")
    tts.speak("Hello world, this is a test.")
    mock_post.assert_not_called()


def test_speak_does_nothing_for_empty_text(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "abc",
        "elevenlabs_api_key": "sk-test", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_post = mocker.patch("src.tts.requests.post")
    tts.speak("   ")
    mock_post.assert_not_called()


def test_speak_calls_elevenlabs_with_correct_params(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "voice-abc",
        "elevenlabs_api_key": "sk-test-key", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"mp3data"
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This is a test sentence for the voice system.")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "voice-abc" in call_kwargs[0][0]
    assert call_kwargs[1]["headers"]["xi-api-key"] == "sk-test-key"
    assert "This is a test sentence" in call_kwargs[1]["json"]["text"]


def test_speak_enqueues_audio_bytes(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "v1",
        "elevenlabs_api_key": "sk-x", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"fakemp3"
    mocker.patch("src.tts.requests.post", return_value=mock_response)
    mock_play = mocker.patch("src.tts._play_audio")

    tts.speak("The quick brown fox jumps over the lazy dog.")

    mock_play.assert_called_once_with(b"fakemp3")


def test_list_voices_returns_name_and_id(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "voices": [
            {"voice_id": "id1", "name": "Rachel"},
            {"voice_id": "id2", "name": "Adam"},
        ]
    }
    mocker.patch("src.tts.config.load", return_value={
        "provider": "elevenlabs", "elevenlabs_api_key": "sk-test", "openai_api_key": ""
    })
    mocker.patch("src.tts.requests.get", return_value=mock_response)

    voices = tts.list_voices()

    assert len(voices) == 2
    assert voices[0] == {"voice_id": "id1", "name": "Rachel"}
    assert voices[1] == {"voice_id": "id2", "name": "Adam"}


def test_speak_routes_to_openai_when_provider_is_openai(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "openai", "voice_id": "v1",
        "elevenlabs_api_key": "", "openai_api_key": "sk-oai",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"oaiaudio"
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This sentence is long enough to be spoken aloud.")

    call_url = mock_post.call_args[0][0]
    assert "openai.com" in call_url
    assert mock_post.call_args[1]["json"]["voice"] == "nova"


def test_list_voices_returns_openai_fixed_voices(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "provider": "openai", "elevenlabs_api_key": "", "openai_api_key": "sk-oai"
    })
    voices = tts.list_voices(provider="openai")
    assert len(voices) == 6
    names = [v["name"] for v in voices]
    assert "Nova" in names


def test_speak_routes_to_google_when_provider_is_google(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "google", "voice_id": "v1",
        "elevenlabs_api_key": "", "openai_api_key": "",
        "google_api_key": "AIza-test", "google_voice": "en-US-Neural2-C",
    })
    import base64
    fake_audio = base64.b64encode(b"fakemp3").decode()
    mock_response = MagicMock()
    mock_response.json.return_value = {"audioContent": fake_audio}
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This sentence is long enough to be spoken aloud.")

    call_url = mock_post.call_args[0][0]
    assert "texttospeech.googleapis.com" in call_url

def test_list_voices_returns_google_neural2_only(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "voices": [
            {"name": "en-US-Neural2-A", "ssmlGender": "MALE"},
            {"name": "en-US-Neural2-C", "ssmlGender": "FEMALE"},
            {"name": "en-US-Standard-A", "ssmlGender": "MALE"},  # should be filtered out
        ]
    }
    mocker.patch("src.tts.requests.get", return_value=mock_response)
    voices = tts.list_voices(provider="google", api_key="AIza-test")
    assert len(voices) == 2
    assert all("Neural2" in v["voice_id"] for v in voices)
    assert not any("Standard" in v["voice_id"] for v in voices)

def test_list_voices_elevenlabs_filters_premade_by_default(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"voices": [
        {"voice_id": "id1", "name": "Rachel"},
        {"voice_id": "id2", "name": "Adam"},
    ]}
    mock_get = mocker.patch("src.tts.requests.get", return_value=mock_response)
    tts.list_voices(provider="elevenlabs", api_key="sk-test")
    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["category"] == "premade"

def test_list_voices_elevenlabs_all_skips_category_filter(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"voices": []}
    mock_get = mocker.patch("src.tts.requests.get", return_value=mock_response)
    tts.list_voices(provider="elevenlabs", api_key="sk-test", premade_only=False)
    call_kwargs = mock_get.call_args
    assert "category" not in call_kwargs[1].get("params", {})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_tts.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.tts'`

- [ ] **Step 3: Implement src/tts.py**

```python
import base64
import subprocess
import threading
import queue

import requests

from src import config

_EL_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_EL_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
_OAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_GOOGLE_VOICES_URL = "https://texttospeech.googleapis.com/v1/voices"

OPENAI_VOICES = ["alloy", "echo", "fissure", "nova", "onyx", "shimmer"]

_audio_queue: queue.Queue = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


def _play_audio(mp3_bytes: bytes) -> None:
    proc = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"],
        stdin=subprocess.PIPE,
    )
    proc.communicate(mp3_bytes)


def _audio_worker() -> None:
    while True:
        item = _audio_queue.get()
        if item is None:
            break
        _play_audio(item)
        _audio_queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_audio_worker, daemon=True)
            _worker.start()


def _speak_elevenlabs(text: str, cfg: dict) -> None:
    resp = requests.post(
        _EL_TTS_URL.format(voice_id=cfg["voice_id"]),
        headers={"xi-api-key": cfg["elevenlabs_api_key"], "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=15,
    )
    resp.raise_for_status()
    _audio_queue.put(resp.content)


def _speak_openai(text: str, cfg: dict) -> None:
    resp = requests.post(
        _OAI_TTS_URL,
        headers={"Authorization": f"Bearer {cfg['openai_api_key']}", "Content-Type": "application/json"},
        json={
            "model": cfg.get("openai_model", "tts-1"),
            "input": text,
            "voice": cfg.get("openai_voice", "nova"),
        },
        timeout=15,
    )
    resp.raise_for_status()
    _audio_queue.put(resp.content)


def _speak_google(text: str, cfg: dict) -> None:
    resp = requests.post(
        f"{_GOOGLE_TTS_URL}?key={cfg['google_api_key']}",
        json={
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": cfg.get("google_voice", "en-US-Neural2-C")},
            "audioConfig": {"audioEncoding": "MP3"},
        },
        timeout=15,
    )
    resp.raise_for_status()
    audio_bytes = base64.b64decode(resp.json()["audioContent"])
    _audio_queue.put(audio_bytes)


def speak(text: str) -> None:
    cfg = config.load()
    if not cfg["enabled"] or not text.strip():
        return
    _ensure_worker()
    provider = cfg.get("provider", "elevenlabs")
    if provider == "openai":
        _speak_openai(text, cfg)
    elif provider == "google":
        _speak_google(text, cfg)
    else:
        _speak_elevenlabs(text, cfg)


def list_voices(provider: str | None = None, api_key: str | None = None, premade_only: bool = True) -> list[dict]:
    cfg = config.load()
    provider = provider or cfg.get("provider", "elevenlabs")
    if provider == "openai":
        return [{"voice_id": v, "name": v.capitalize()} for v in OPENAI_VOICES]
    if provider == "google":
        key = api_key or cfg["google_api_key"]
        resp = requests.get(
            f"{_GOOGLE_VOICES_URL}?key={key}&languageCode=en-US",
            timeout=10,
        )
        resp.raise_for_status()
        voices = [
            v for v in resp.json()["voices"]
            if "Neural2" in v["name"]
        ]
        return [{"voice_id": v["name"], "name": v["name"]} for v in sorted(voices, key=lambda x: x["name"])]
    # ElevenLabs
    key = api_key or cfg["elevenlabs_api_key"]
    params = {}
    if premade_only:
        params["category"] = "premade"
    resp = requests.get(
        _EL_VOICES_URL,
        headers={"xi-api-key": key},
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return [{"voice_id": v["voice_id"], "name": v["name"]} for v in resp.json()["voices"]]
```

**Note on `premade_only` (ElevenLabs):** ElevenLabs has 10,000+ community voices, but the Voice Library is NOT accessible via API on the free tier. The `/v1/voices` endpoint returns the user's own voices plus the official premade voices. Passing `category=premade` filters to ~30–50 official ElevenLabs voices — the sensible default for new users. Setting `premade_only=False` (triggered by `/voice list all`) shows everything including the user's cloned/generated voices.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_tts.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/tts.py tests/test_tts.py && git commit -m "feat: multi-provider TTS with ElevenLabs, OpenAI, and Google backends"
```

---

## Task 5: stop-hook.py

**Files:**
- Create: `hooks/stop-hook.py`
- Create: `tests/test_stop_hook.py`

Reads Claude Code's stop hook JSON from stdin, extracts the last assistant message text, filters it, and speaks it.

- [ ] **Step 1: Write failing tests**

Create `tests/test_stop_hook.py`:

```python
import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock
import pytest


def _run_hook(payload: dict):
    """Helper: run stop-hook main() with payload on stdin."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "stop_hook",
        Path(__file__).parent.parent / "hooks" / "stop-hook.py"
    )
    mod = importlib.util.module_from_spec(spec)
    with patch("sys.stdin", StringIO(json.dumps(payload))):
        spec.loader.exec_module(mod)
    return mod


def test_speaks_last_assistant_text(mocker):
    mock_speak = mocker.patch("src.tts.speak")
    payload = {
        "transcript": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language known for its readability."},
        ]
    }
    _run_hook(payload)
    mock_speak.assert_called_once()
    spoken = mock_speak.call_args[0][0]
    assert "Python is a high-level programming language" in spoken


def test_skips_when_no_assistant_message(mocker):
    mock_speak = mocker.patch("src.tts.speak")
    payload = {"transcript": [{"role": "user", "content": "Hello"}]}
    _run_hook(payload)
    mock_speak.assert_not_called()


def test_handles_content_block_array(mocker):
    mock_speak = mocker.patch("src.tts.speak")
    payload = {
        "transcript": [
            {"role": "user", "content": "Show me code"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Here is an explanation of how this works in practice."},
                {"type": "tool_use", "name": "bash", "input": {"command": "ls"}},
            ]},
        ]
    }
    _run_hook(payload)
    mock_speak.assert_called_once()
    spoken = mock_speak.call_args[0][0]
    assert "Here is an explanation" in spoken
    assert "bash" not in spoken


def test_exits_silently_on_empty_filtered_text(mocker):
    mock_speak = mocker.patch("src.tts.speak")
    payload = {
        "transcript": [
            {"role": "user", "content": "Show code"},
            {"role": "assistant", "content": "```python\nprint('hi')\n```"},
        ]
    }
    _run_hook(payload)
    # speak() called with empty/whitespace-only — tts.speak handles the no-op
    if mock_speak.called:
        assert mock_speak.call_args[0][0].strip() == ""
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_stop_hook.py -v
```

Expected: errors loading `hooks/stop-hook.py`

- [ ] **Step 3: Implement hooks/stop-hook.py**

```python
#!/usr/bin/env python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import filter as f, tts


def extract_last_assistant_text(transcript: list) -> str:
    for msg in reversed(transcript):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                return " ".join(
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                )
            return content
    return ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    transcript = data.get("transcript", [])
    raw_text = extract_last_assistant_text(transcript)
    filtered = f.filter_response(raw_text)
    tts.speak(filtered)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/test_stop_hook.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add hooks/stop-hook.py tests/test_stop_hook.py && git commit -m "feat: Claude Code stop hook extracts and speaks last assistant message"
```

---

## Task 6: Slash Command Scripts

**Files:**
- Create: `commands/voice_on.py`
- Create: `commands/voice_off.py`
- Create: `commands/voice_list.py`
- Create: `commands/voice_pick.py`

These are run directly by Claude via the Bash tool when slash commands are invoked. Voice pick writes to config so selection persists across restarts.

- [ ] **Step 1: Create commands/voice_on.py**

```python
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

config.set_enabled(True)
print("Voice is now ON.")
```

- [ ] **Step 2: Create commands/voice_off.py**

```python
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

config.set_enabled(False)
print("Voice is now OFF.")
```

- [ ] **Step 3: Create commands/voice_list.py**

```python
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config, tts

cfg = config.load()
provider = cfg.get("provider", "elevenlabs")

if not cfg.get("elevenlabs_api_key") and not cfg.get("openai_api_key") and not cfg.get("google_api_key"):
    print("No API key set. Run setup.py first.")
    sys.exit(1)

premade_only = "--all" not in sys.argv and "all" not in sys.argv

voices = tts.list_voices(premade_only=premade_only)
current = cfg.get("voice_id") or cfg.get("openai_voice") or cfg.get("google_voice")

if provider == "elevenlabs" and premade_only:
    print("Showing premade voices. Use '/voice list all' to see all voices including your own.\n")

print(f"{'NAME':<30} {'ID':<40} {'ACTIVE'}")
print("-" * 75)
for v in sorted(voices, key=lambda x: x["name"]):
    active = "* current" if v["voice_id"] == current else ""
    print(f"{v['name']:<30} {v['voice_id']:<40} {active}")
```

- [ ] **Step 4: Create commands/voice_pick.py**

Takes voice name or ID as argv[1]. Saves selection to config — persists between restarts.

```python
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config, tts

if len(sys.argv) < 2:
    print("Usage: voice_pick.py <voice-name-or-id>")
    sys.exit(1)

query = " ".join(sys.argv[1:]).strip()
cfg = config.load()

if not cfg["api_key"]:
    print("No API key set. Run setup.py first.")
    sys.exit(1)

voices = tts.list_voices(cfg["api_key"])

# Match by exact ID first, then case-insensitive name
match = next((v for v in voices if v["voice_id"] == query), None)
if not match:
    match = next((v for v in voices if v["name"].lower() == query.lower()), None)
if not match:
    print(f"No voice found matching '{query}'. Run /voice list to see options.")
    sys.exit(1)

config.set_voice(match["voice_id"])
print(f"Voice set to '{match['name']}' (ID: {match['voice_id']}). This selection persists between sessions.")
```

- [ ] **Step 5: Create commands/voice_verbosity.py**

```python
#!/usr/bin/env python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

if len(sys.argv) < 2 or sys.argv[1] not in ("low", "medium", "high"):
    print("Usage: voice_verbosity.py <low|medium|high>")
    print("  low    — Claude summarizes lists; max 2 bullets per response")
    print("  medium — Claude limits lists to 5 items")
    print("  high   — no constraints on format")
    sys.exit(1)

level = sys.argv[1]
config.set_verbosity(level)
print(f"VERBOSITY:{level}")
```

Note: The script prints `VERBOSITY:<level>` as a signal. The slash command markdown file (Task 7) reads this and injects the directive into the conversation.

- [ ] **Step 6: Create commands/voice_provider.py**

```python
#!/usr/bin/env python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import config

if len(sys.argv) < 2 or sys.argv[1] not in ("elevenlabs", "openai", "google"):
    print("Usage: voice_provider.py <elevenlabs|openai|google>")
    sys.exit(1)

provider = sys.argv[1]
config.set_provider(provider)
print(f"TTS provider set to '{provider}'.")
```

- [ ] **Step 7: Smoke-test the scripts manually**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice"
python commands/voice_on.py
python commands/voice_off.py
```

Expected output:
```
Voice is now ON.
Voice is now OFF.
```

- [ ] **Step 8: Commit**

```bash
git add commands/ && git commit -m "feat: slash command Python scripts for voice on/off/list/pick/verbosity/provider"
```

---

## Task 7: Slash Command Markdown Files

**Files:**
- Create: `.claude/commands/voice/on.md`
- Create: `.claude/commands/voice/off.md`
- Create: `.claude/commands/voice/list.md`
- Create: `.claude/commands/voice/pick.md`

- [ ] **Step 1: Create .claude/commands/voice/on.md**

```bash
mkdir -p ".claude/commands/voice"
```

```markdown
Run this command to enable voice TTS:

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_on.py"
```

Print the exact output to the user.
```

- [ ] **Step 2: Create .claude/commands/voice/off.md**

```markdown
Run this command to disable voice TTS:

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_off.py"
```

Print the exact output to the user.
```

- [ ] **Step 3: Create .claude/commands/voice/list.md**

```markdown
Run this command to list available voices for the current TTS provider:

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_list.py" $ARGUMENTS
```

Print the full table output to the user. If the provider is ElevenLabs and no arguments were given, note that `/voice list all` shows all voices including user-created ones.
```

- [ ] **Step 4: Create .claude/commands/voice/pick.md**

```markdown
Run this command to select a voice by name or ID. The argument is: $ARGUMENTS

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_pick.py" "$ARGUMENTS"
```

Print the exact output to the user. The selected voice persists between sessions.
```

- [ ] **Step 5: Create .claude/commands/voice/verbosity.md**

```markdown
Run this command to set voice verbosity. The level is: $ARGUMENTS

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_verbosity.py" "$ARGUMENTS"
```

Then, based on the level, immediately adopt the following rule for the rest of this conversation:

**If level is "low":** Do not use bullet lists. Summarize any list as a single sentence. Example: "There are four considerations: X, Y, Z, and one more."

**If level is "medium":** When using bullet lists, limit to 3 items. If you have more, include the most important 3 and note how many were omitted (e.g. "...and 2 more").

**If level is "high":** No special constraints on format or length.

Confirm to the user: "Verbosity set to [level] — taking effect now in this conversation."
```

- [ ] **Step 6: Create .claude/commands/voice/provider.md**

```markdown
Run this command to switch the TTS provider. The provider is: $ARGUMENTS

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_provider.py" "$ARGUMENTS"
```

Print the exact output to the user.
```

- [ ] **Step 7: Commit**

```bash
git add .claude/ && git commit -m "feat: slash command markdown files for /voice on/off/list/pick/verbosity/provider"
```

---

## Task 8: Desktop Daemon — Accessibility Tree Discovery

**Files:**
- Create: `daemon/inspect-tree.py`

Before implementing the daemon, we need to know where Claude Desktop puts its response text in the Windows accessibility tree. This task runs the inspector once to find the right selectors.

- [ ] **Step 1: Create daemon/inspect-tree.py**

```python
#!/usr/bin/env python
"""
Run once with Claude Desktop open to discover the accessibility tree structure.
Output shows control types, names, and text content so we can find the right selectors.
Usage: python daemon/inspect-tree.py > tree-dump.txt
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pywinauto import Application, Desktop
except ImportError:
    print("pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)


def dump_element(elem, depth=0, max_depth=6):
    if depth > max_depth:
        return
    try:
        info = elem.element_info
        text = ""
        try:
            text = elem.window_text()[:120].replace("\n", "\\n")
        except Exception:
            pass
        print(
            "  " * depth
            + json.dumps({
                "type": info.control_type,
                "name": info.name[:80] if info.name else "",
                "class": info.class_name,
                "text": text,
            })
        )
        for child in elem.children():
            dump_element(child, depth + 1, max_depth)
    except Exception as e:
        print("  " * depth + f"[error: {e}]")


def main():
    print("Looking for Claude window...", file=sys.stderr)
    try:
        app = Application(backend="uia").connect(title_re=".*Claude.*", timeout=5)
        window = app.top_window()
        print(f"Found: {window.window_text()}", file=sys.stderr)
        dump_element(window.wrapper_object())
    except Exception as e:
        print(f"Could not connect to Claude Desktop: {e}", file=sys.stderr)
        print("Make sure Claude Desktop is open and visible.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Open Claude Desktop and run the inspector**

Open Claude Desktop and have a conversation so at least one assistant response is visible. Then run:

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice"
python daemon/inspect-tree.py > daemon/tree-dump.txt 2>&1
```

- [ ] **Step 3: Find the assistant response container**

Open `daemon/tree-dump.txt` and search for text that matches Claude's response content. Look for:
- A container element that holds the full assistant response
- Its `type`, `name`, and `class` values at the top level of the response area
- Note the depth path from the window root down to this element

Record the selector strategy in a comment at the top of `daemon/desktop-daemon.py` (next task).

- [ ] **Step 4: Commit discovery artifacts**

```bash
git add daemon/inspect-tree.py daemon/tree-dump.txt && git commit -m "feat: accessibility tree inspector for Claude Desktop daemon"
```

---

## Task 9: Desktop Daemon — Implementation

**Files:**
- Create: `daemon/desktop-daemon.py`

> **Note:** The selector in `_get_response_text()` must be filled in based on the `tree-dump.txt` findings from Task 8. The placeholder comment marks where to insert the discovered selector.

- [ ] **Step 1: Implement daemon/desktop-daemon.py**

```python
#!/usr/bin/env python
"""
Watches Claude Desktop's accessibility tree for new assistant responses.
Speaks each sentence via ElevenLabs as it streams in.
Run: python daemon/desktop-daemon.py
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config
from src.filter import filter_response
from src.tts import speak

try:
    from pywinauto import Application
except ImportError:
    print("pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_POLL_INTERVAL = 0.1  # seconds


def _connect_to_claude() -> object | None:
    try:
        app = Application(backend="uia").connect(title_re=".*Claude.*", timeout=3)
        return app.top_window()
    except Exception:
        return None


def _get_response_text(window) -> str:
    """
    Extract the latest assistant response text from Claude Desktop's UI tree.
    SELECTOR: Update this function based on tree-dump.txt findings from Task 8.
    Look for the element type/name path that contains the assistant response text.
    """
    try:
        # Replace with the discovered selector, e.g.:
        # response_area = window.child_window(control_type="Document", found_index=0)
        # return response_area.window_text()
        texts = window.descendants(control_type="Text")
        # Filter to last substantial text block (heuristic until selector is refined)
        candidates = [t for t in texts if len(t.window_text()) > 20]
        if not candidates:
            return ""
        return candidates[-1].window_text()
    except Exception:
        return ""


class SentenceBuffer:
    def __init__(self):
        self._prev = ""
        self._in_fence = False
        self._partial = ""

    def reset(self):
        self._prev = ""
        self._in_fence = False
        self._partial = ""

    def feed(self, current_text: str) -> list[str]:
        """Feed current full text, returns list of new speakable sentences."""
        if not current_text.startswith(self._prev):
            self.reset()

        new_chunk = current_text[len(self._prev):]
        self._prev = current_text

        if not new_chunk:
            return []

        # Track triple-backtick fences
        fence_count = new_chunk.count("```")
        if fence_count % 2 == 1:
            self._in_fence = not self._in_fence
        if self._in_fence:
            return []

        self._partial += new_chunk
        parts = _SENTENCE_END.split(self._partial)

        # All but the last part are complete sentences
        complete = parts[:-1]
        self._partial = parts[-1]

        result = []
        for sentence in complete:
            filtered = filter_response(sentence.strip())
            if len(filtered.split()) >= 4:
                result.append(filtered)
        return result


def main():
    print("Claude Desktop voice daemon starting...", flush=True)
    buf = SentenceBuffer()
    prev_text = ""

    while True:
        if not config.is_enabled():
            time.sleep(0.5)
            buf.reset()
            prev_text = ""
            continue

        window = _connect_to_claude()
        if window is None:
            print("Claude Desktop not found, retrying...", flush=True)
            time.sleep(3)
            continue

        current_text = _get_response_text(window)

        if current_text != prev_text:
            if not current_text.startswith(prev_text or ""):
                buf.reset()
            sentences = buf.feed(current_text)
            for sentence in sentences:
                speak(sentence)
            prev_text = current_text

        time.sleep(_POLL_INTERVAL)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Refine the selector using tree-dump.txt**

Open `daemon/tree-dump.txt`. Find the element that contains assistant response text. Update `_get_response_text()` to use the specific `child_window()` selector. For example, if the dump shows a `Document` control type at depth 4:

```python
def _get_response_text(window) -> str:
    try:
        # Discovered from tree-dump.txt: Document control at depth 4
        area = window.child_window(control_type="Document", found_index=0)
        return area.window_text()
    except Exception:
        return ""
```

- [ ] **Step 3: Manual test — run the daemon with Claude Desktop open**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice"
python commands/voice_on.py
python daemon/desktop-daemon.py
```

Open Claude Desktop and send a message. Expected: each sentence of Claude's response is spoken aloud as it streams in.

If no audio, check: (a) voice is enabled (`voice_on.py` was run), (b) ffplay is installed (`ffplay -version`), (c) `_get_response_text()` is returning non-empty text (add a `print(current_text[:80])` to verify).

- [ ] **Step 4: Commit**

```bash
git add daemon/desktop-daemon.py && git commit -m "feat: Claude Desktop UIAutomation daemon with sentence-level streaming TTS"
```

---

## Task 10: setup.py

**Files:**
- Create: `setup.py`

First-run setup: prompts for API key, verifies it against ElevenLabs, writes config, checks ffmpeg, registers the stop hook in `~/.claude/settings.json` (merging into existing hooks, never overwriting).

- [ ] **Step 1: Implement setup.py**

```python
#!/usr/bin/env python
"""First-run setup for claude-voice."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent / "hooks" / "stop-hook.py"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
OPENAI_VOICES = ["alloy", "echo", "fissure", "nova", "onyx", "shimmer"]


def check_ffmpeg() -> bool:
    return shutil.which("ffplay") is not None


def verify_elevenlabs_key(api_key: str) -> list[dict] | None:
    import requests
    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["voices"]
        return None
    except Exception:
        return None


def verify_openai_key(api_key: str) -> bool:
    import requests
    try:
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "tts-1", "input": "test", "voice": "nova"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def register_hook(hook_command: str) -> None:
    settings = {}
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.setdefault("Stop", [])

    stop_hooks = [
        h for h in stop_hooks
        if not any("stop-hook.py" in str(cmd.get("command", "")) for cmd in h.get("hooks", []))
    ]

    stop_hooks.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_command}],
    })
    hooks["Stop"] = stop_hooks
    settings["hooks"] = hooks

    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def setup_elevenlabs(cfg: dict) -> dict:
    api_key = input("Enter your ElevenLabs API key (from elevenlabs.io): ").strip()
    if not api_key:
        print("No API key provided.")
        sys.exit(1)
    print("Verifying ElevenLabs API key...", end=" ", flush=True)
    voices = verify_elevenlabs_key(api_key)
    if voices is None:
        print("FAILED\nInvalid API key or network error.")
        sys.exit(1)
    print(f"OK ({len(voices)} voices available)")
    print("\nAvailable voices:")
    for i, v in enumerate(voices[:10], 1):
        print(f"  {i:2}. {v['name']}")
    if len(voices) > 10:
        print(f"  ... and {len(voices) - 10} more (use /voice list to see all)")
    choice = input("\nEnter voice number for default [1]: ").strip() or "1"
    try:
        selected = voices[int(choice) - 1]
    except (ValueError, IndexError):
        selected = voices[0]
    print(f"Selected: {selected['name']}")
    cfg["elevenlabs_api_key"] = api_key
    cfg["voice_id"] = selected["voice_id"]
    return cfg


def setup_openai(cfg: dict) -> dict:
    api_key = input("Enter your OpenAI API key (from platform.openai.com): ").strip()
    if not api_key:
        print("No API key provided.")
        sys.exit(1)
    print("Verifying OpenAI API key...", end=" ", flush=True)
    if not verify_openai_key(api_key):
        print("FAILED\nInvalid API key or network error.")
        sys.exit(1)
    print("OK")
    print("\nAvailable voices:")
    for i, v in enumerate(OPENAI_VOICES, 1):
        print(f"  {i}. {v}")
    choice = input("\nEnter voice number for default [4 = nova]: ").strip() or "4"
    try:
        selected = OPENAI_VOICES[int(choice) - 1]
    except (ValueError, IndexError):
        selected = "nova"
    print(f"Selected: {selected}")
    cfg["openai_api_key"] = api_key
    cfg["openai_voice"] = selected
    cfg["openai_model"] = "tts-1"
    return cfg


def verify_google_key(api_key: str) -> list[dict] | None:
    try:
        resp = requests.get(
            f"https://texttospeech.googleapis.com/v1/voices?key={api_key}&languageCode=en-US",
            timeout=10,
        )
        if resp.status_code == 200:
            return [v for v in resp.json()["voices"] if "Neural2" in v["name"]]
        return None
    except Exception:
        return None

def setup_google(cfg: dict) -> dict:
    api_key = input("Enter your Google Cloud TTS API key: ").strip()
    if not api_key:
        print("No API key provided.")
        sys.exit(1)
    print("Verifying Google API key...", end=" ", flush=True)
    voices = verify_google_key(api_key)
    if voices is None:
        print("FAILED\nInvalid API key or network error.")
        sys.exit(1)
    print(f"OK ({len(voices)} Neural2 voices available)")
    print("\nAvailable en-US Neural2 voices:")
    for i, v in enumerate(sorted(voices, key=lambda x: x["name"]), 1):
        print(f"  {i:2}. {v['name']}")
    choice = input("\nEnter voice number for default [1]: ").strip() or "1"
    try:
        selected = sorted(voices, key=lambda x: x["name"])[int(choice) - 1]
    except (ValueError, IndexError):
        selected = {"name": "en-US-Neural2-C"}
    print(f"Selected: {selected['name']}")
    cfg["google_api_key"] = api_key
    cfg["google_voice"] = selected["name"]
    return cfg


def main():
    print("=== Claude Voice Setup ===\n")

    if check_ffmpeg():
        print("✓ ffplay found")
    else:
        print("✗ ffplay not found. Install ffmpeg:")
        print("  winget install ffmpeg")
        print("  Then re-run setup.py\n")
        sys.exit(1)

    print("\nWhich TTS provider do you want to use?")
    print("  1. ElevenLabs (free tier: 10k chars/month, best quality, named voices)")
    print("  2. OpenAI     (no free tier, ~$15/1M chars, 6 voices, simplest)")
    print("  3. Google     (free tier: 1M chars/month, en-US Neural2 voices)")
    provider_choice = input("\nEnter 1, 2, or 3 [1]: ").strip() or "1"
    if provider_choice == "2":
        provider = "openai"
    elif provider_choice == "3":
        provider = "google"
    else:
        provider = "elevenlabs"
    print(f"Using: {provider}\n")

    sys.path.insert(0, str(Path(__file__).parent))
    from src import config as cfg_module

    cfg = cfg_module._DEFAULTS.copy()
    cfg["provider"] = provider

    if provider == "elevenlabs":
        cfg = setup_elevenlabs(cfg)
        also = input("\nAlso set up OpenAI as a backup provider? [y/N]: ").strip().lower()
        if also == "y":
            cfg = setup_openai(cfg)
        also2 = input("\nAlso set up Google as a backup provider? [y/N]: ").strip().lower()
        if also2 == "y":
            cfg = setup_google(cfg)
    elif provider == "openai":
        cfg = setup_openai(cfg)
        also = input("\nAlso set up ElevenLabs as a backup provider? [y/N]: ").strip().lower()
        if also == "y":
            cfg = setup_elevenlabs(cfg)
        also2 = input("\nAlso set up Google as a backup provider? [y/N]: ").strip().lower()
        if also2 == "y":
            cfg = setup_google(cfg)
    else:
        cfg = setup_google(cfg)
        also = input("\nAlso set up ElevenLabs as a backup provider? [y/N]: ").strip().lower()
        if also == "y":
            cfg = setup_elevenlabs(cfg)
        also2 = input("\nAlso set up OpenAI as a backup provider? [y/N]: ").strip().lower()
        if also2 == "y":
            cfg = setup_openai(cfg)

    cfg_module.save(cfg)
    print(f"\n✓ Config saved to {cfg_module.CONFIG_PATH}")

    hook_cmd = f'python "{HOOK_SCRIPT.resolve()}"'
    register_hook(hook_cmd)
    print(f"✓ Stop hook registered in {SETTINGS_PATH}")

    desktop_config = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if desktop_config.exists():
        with open(desktop_config) as f:
            dc = json.load(f)
    else:
        dc = {}
    mcp_cmd = str((Path(__file__).parent / "mcp_server" / "voice-mcp-server.py").resolve())
    dc.setdefault("mcpServers", {})["claude-voice"] = {
        "command": "python",
        "args": [mcp_cmd],
    }
    desktop_config.parent.mkdir(parents=True, exist_ok=True)
    with open(desktop_config, "w") as f:
        json.dump(dc, f, indent=2)
    print(f"✓ MCP server registered in {desktop_config}")
    print("  Restart Claude Desktop for the voice prompts to appear.")

    print("\n=== Setup complete ===")
    print("Run /voice on in Claude Code to enable voice.")
    print("Run 'python daemon/desktop-daemon.py' to start the Claude Desktop daemon.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run setup.py end-to-end**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice"
python setup.py
```

Walk through the prompts. Expected final output includes:
```
✓ Config saved to C:\Users\SJG\.claude\voice-config.json
✓ Stop hook registered in C:\Users\SJG\.claude\settings.json
=== Setup complete ===
```

- [ ] **Step 3: Verify hook was merged into settings.json (not overwritten)**

```bash
python -c "import json; d=json.load(open('C:/Users/SJG/.claude/settings.json')); print(json.dumps(d.get('hooks', {}), indent=2))"
```

Expected: existing keys in settings.json are preserved, and `hooks.Stop` contains the new entry alongside any pre-existing entries.

- [ ] **Step 4: Commit**

```bash
git add setup.py && git commit -m "feat: first-run setup with API key verification, voice selection, hook registration"
```

---

## Task 11: End-to-End Integration Test

Manual smoke test of the full system.

- [ ] **Step 1: Verify full test suite still passes**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice" && python -m pytest tests/ -v
```

Expected: all tests pass (no regressions).

- [ ] **Step 2: Test Claude Code path**

In a Claude Code session:
```
/voice on
```
Ask Claude any prose question (e.g. "What is the capital of France?"). Expected: Claude's response is spoken aloud after it finishes generating. Code blocks in responses should not be spoken.

- [ ] **Step 3: Test voice persistence**

```
/voice list
/voice pick Rachel
```
Close and reopen Claude Code. Run `/voice list` again. Expected: Rachel is still marked as current.

- [ ] **Step 4: Test voice off**

```
/voice off
```
Ask Claude another question. Expected: silence (no audio).

- [ ] **Step 5: Test Claude Desktop path**

Open Claude Desktop. Start the daemon:
```bash
python commands/voice_on.py
python daemon/desktop-daemon.py
```
Send Claude Desktop a message. Expected: sentences are spoken as they stream in, before the full response is complete.

- [ ] **Step 6: Final commit**

```bash
git add -A && git commit -m "feat: complete ElevenLabs voice system — Claude Code + Desktop"
```

---

## Task 12: MCP Prompt Server (Claude Desktop Verbosity)

**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/voice-mcp-server.py`

Exposes three named prompts in Claude Desktop's prompt picker. Selecting one injects the verbosity directive into the conversation immediately and writes to config — same effect as `/voice verbosity` in Claude Code.

- [ ] **Step 1: Create mcp_server/__init__.py**

```bash
touch mcp_server/__init__.py
```

- [ ] **Step 2: Implement mcp_server/voice-mcp-server.py**

```python
#!/usr/bin/env python
"""MCP prompt server — exposes voice verbosity prompts for Claude Desktop."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from src import config

_DIRECTIVES = {
    "low": (
        "For the rest of this conversation, do not use long bullet lists. "
        "If you would normally list 3 or more items, summarize them in 1–2 sentences instead "
        "(e.g. \"There are four considerations: the main one is X, along with Y, Z, and one more\"). "
        "Maximum 2 bullet points per response."
    ),
    "medium": (
        "For the rest of this conversation, when using bullet lists, limit to 5 items. "
        "If you have more, include the most important 5 and note how many were omitted."
    ),
    "high": (
        "No special constraints on response format or length."
    ),
}

server = Server("claude-voice")


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="voice-verbosity-low",
            description="Voice: Low verbosity — Claude summarizes lists, max 2 bullets",
        ),
        types.Prompt(
            name="voice-verbosity-medium",
            description="Voice: Medium verbosity — Claude limits lists to 5 items",
        ),
        types.Prompt(
            name="voice-verbosity-high",
            description="Voice: High verbosity — no format constraints",
        ),
    ]


@server.get_prompt()
async def get_prompt(
    name: str, arguments: dict[str, str] | None = None
) -> types.GetPromptResult:
    level_map = {
        "voice-verbosity-low": "low",
        "voice-verbosity-medium": "medium",
        "voice-verbosity-high": "high",
    }
    if name not in level_map:
        raise ValueError(f"Unknown prompt: {name}")

    level = level_map[name]
    config.set_verbosity(level)

    return types.GetPromptResult(
        description=f"Voice verbosity set to {level}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=_DIRECTIVES[level]),
            )
        ],
    )


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Verify the server starts without error**

```bash
cd "C:/Users/SJG/Documents/CodePlayground/claude voice"
python mcp_server/voice-mcp-server.py &
sleep 2 && kill %1
```

Expected: no import errors, process exits cleanly when killed.

- [ ] **Step 4: Verify Claude Desktop registration (setup.py already handles this)**

Check `%APPDATA%\Claude\claude_desktop_config.json` contains the entry:

```bash
python -c "import json,os; d=json.load(open(os.environ['APPDATA']+'/Claude/claude_desktop_config.json')); print(json.dumps(d.get('mcpServers',{}), indent=2))"
```

Expected: `claude-voice` key pointing to `voice-mcp-server.py`.

- [ ] **Step 5: Manual test in Claude Desktop**

Restart Claude Desktop. Open a new conversation. Click the prompt picker (the "+" or slash icon in the input area). Expected: three "Voice:" prompts appear. Select "Voice: Low verbosity". Expected: the verbosity directive appears in the conversation and Claude acknowledges it.

- [ ] **Step 6: Verify config was updated**

```bash
python -c "from src import config; print(config.load()['verbosity'])"
```

Expected: `low`

- [ ] **Step 7: Commit**

```bash
git add mcp_server/ && git commit -m "feat: MCP prompt server for Claude Desktop verbosity control"
```
