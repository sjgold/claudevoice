#!/usr/bin/env python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import filter as f, tts


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    raw_text = data.get("last_assistant_message", "")
    if not raw_text:
        return
    filtered = f.filter_response(raw_text)
    tts.speak(filtered)
    tts._audio_queue.join()


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
