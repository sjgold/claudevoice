#!/usr/bin/env python
"""First-run setup for claude-voice."""
import json
import os
import shutil
import sys
from pathlib import Path

import requests

HOOK_SCRIPT = Path(__file__).parent / "hooks" / "stop-hook.py"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
OPENAI_VOICES = ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]


def check_ffmpeg() -> bool:
    return shutil.which("ffplay") is not None


def verify_elevenlabs_key(api_key: str) -> list[dict] | None:
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


def register_hook(hook_command: str) -> None:
    settings = {}
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                settings = json.load(f)
        except (json.JSONDecodeError, ValueError):
            settings = {}

    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.get("Stop", [])

    # Remove any existing claude-voice hook entry
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

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def register_mcp_server() -> None:
    desktop_config = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    if not desktop_config.parent.exists():
        print("Claude Desktop config directory not found — skipping MCP registration.")
        return

    dc = {}
    if desktop_config.exists():
        try:
            with open(desktop_config) as f:
                dc = json.load(f)
        except (json.JSONDecodeError, ValueError):
            dc = {}

    mcp_cmd = str((Path(__file__).parent / "mcp_server" / "voice-mcp-server.py").resolve())
    dc.setdefault("mcpServers", {})["claude-voice"] = {
        "command": "python",
        "args": [mcp_cmd],
    }
    with open(desktop_config, "w") as f:
        json.dump(dc, f, indent=2)
    print(f"✓ MCP server registered in {desktop_config}")
    print("  Restart Claude Desktop for the voice prompts to appear.")


def setup_elevenlabs(cfg: dict) -> dict:
    api_key = input("Enter your ElevenLabs API key: ").strip()
    if not api_key:
        print("No API key provided.")
        sys.exit(1)
    print("Verifying ElevenLabs API key...", end=" ", flush=True)
    voices = verify_elevenlabs_key(api_key)
    if voices is None:
        print("FAILED\nInvalid API key or network error.")
        sys.exit(1)
    premade = [v for v in voices if v.get("category") == "premade"]
    display = premade if premade else voices
    print(f"OK ({len(display)} premade voices available)")
    print("\nAvailable voices:")
    for i, v in enumerate(display[:10], 1):
        print(f"  {i:2}. {v['name']}")
    if len(display) > 10:
        print(f"  ... and {len(display) - 10} more (use /voice list to see all)")
    choice = input("\nEnter voice number for default [1]: ").strip() or "1"
    try:
        selected = display[int(choice) - 1]
    except (ValueError, IndexError):
        selected = display[0]
    print(f"Selected: {selected['name']}")
    cfg["elevenlabs_api_key"] = api_key
    cfg["voice_id"] = selected["voice_id"]
    return cfg


def setup_openai(cfg: dict) -> dict:
    api_key = input("Enter your OpenAI API key: ").strip()
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
    voices = sorted(voices, key=lambda x: x["name"])
    print(f"OK ({len(voices)} Neural2 voices available)")
    print("\nAvailable en-US Neural2 voices:")
    for i, v in enumerate(voices, 1):
        print(f"  {i:2}. {v['name']}")
    choice = input("\nEnter voice number for default [1]: ").strip() or "1"
    try:
        selected = voices[int(choice) - 1]
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
        print("✗ ffplay not found. Install ffmpeg: winget install ffmpeg")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parent))
    from src import config as cfg_module

    cfg = cfg_module._DEFAULTS.copy()

    print("\nWhich TTS provider do you want to use?")
    print("  1. ElevenLabs (10k chars/month free, best quality)")
    print("  2. OpenAI     (no free tier, ~$15/1M chars, 6 voices)")
    print("  3. Google     (1M chars/month free, Neural2 voices)")
    provider_choice = input("\nEnter 1, 2, or 3 [1]: ").strip() or "1"
    if provider_choice == "2":
        provider = "openai"
    elif provider_choice == "3":
        provider = "google"
    else:
        provider = "elevenlabs"
    cfg["provider"] = provider
    print(f"Using: {provider}\n")

    if provider == "elevenlabs":
        cfg = setup_elevenlabs(cfg)
    elif provider == "openai":
        cfg = setup_openai(cfg)
    else:
        cfg = setup_google(cfg)

    also = input("\nSet up additional providers? [y/N]: ").strip().lower()
    if also == "y":
        for p in ["elevenlabs", "openai", "google"]:
            if p == provider:
                continue
            ans = input(f"Set up {p}? [y/N]: ").strip().lower()
            if ans == "y":
                if p == "elevenlabs":
                    cfg = setup_elevenlabs(cfg)
                elif p == "openai":
                    cfg = setup_openai(cfg)
                else:
                    cfg = setup_google(cfg)

    cfg_module.save(cfg)
    print(f"\n✓ Config saved to {cfg_module.CONFIG_PATH}")

    hook_cmd = f'python "{HOOK_SCRIPT.resolve()}"'
    register_hook(hook_cmd)
    print(f"✓ Stop hook registered in {SETTINGS_PATH}")

    register_mcp_server()

    print("\n=== Setup complete ===")
    print("Run /voice on in Claude Code to enable voice.")
    print("Run 'python daemon/desktop-daemon.py' to start the Claude Desktop daemon.")


if __name__ == "__main__":
    main()
