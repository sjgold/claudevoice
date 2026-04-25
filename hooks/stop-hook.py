#!/usr/bin/env python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config, filter as f, tts


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    raw_text = data.get("last_assistant_message", "")
    if isinstance(raw_text, list):
        raw_text = " ".join(
            block.get("text", "") for block in raw_text
            if isinstance(block, dict) and block.get("type") == "text"
        )
    if not raw_text:
        return
    cfg = config.load()
    verbosity = cfg.get("verbosity", "2")
    filtered = f.filter_response(raw_text, verbosity=verbosity)
    tts.speak(filtered)
    import threading
    join_thread = threading.Thread(target=tts._audio_queue.join, daemon=True)
    join_thread.start()
    join_thread.join(timeout=30)


if __name__ == "__main__":
    main()
