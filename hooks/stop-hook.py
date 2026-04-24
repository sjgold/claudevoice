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
    if not raw_text:
        return
    filtered = f.filter_response(raw_text)
    tts.speak(filtered)


if __name__ == "__main__":
    main()
