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
provider = cfg.get("provider", "elevenlabs")

voices = tts.list_voices()

match = next((v for v in voices if v["voice_id"] == query), None)
if not match:
    match = next((v for v in voices if v["name"].lower() == query.lower()), None)
if not match:
    print(f"No voice found matching '{query}'. Run /voice list to see options.")
    sys.exit(1)

config.set_voice(match["voice_id"])
print(f"Voice set to '{match['name']}' (ID: {match['voice_id']}). This selection persists between sessions.")
