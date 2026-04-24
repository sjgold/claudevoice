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
