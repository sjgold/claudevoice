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
