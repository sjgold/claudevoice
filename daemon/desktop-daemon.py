#!/usr/bin/env python
"""
Watches Claude Desktop's accessibility tree for new assistant responses.
Speaks each sentence via TTS as it streams in.
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
    from pywinauto import Desktop, Application
except ImportError:
    print("pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_POLL_INTERVAL = 0.1  # seconds

# UI strings that appear in Claude Desktop chrome — not response content
_UI_NOISE = {
    "Click to collapse",
    "Drag to resize",
    "Drag to pin",
    "Type / for commands",
    "Resize sidebar",
    "Skip to content",
    "Arrow keys move the tile.",
}


def _connect_to_claude():
    """Return the Claude Desktop top-level window, or None if not found."""
    try:
        desktop = Desktop(backend="uia")
        all_windows = desktop.windows()
        target = next(
            (w for w in all_windows if w.window_text().strip() == "Claude"),
            None
        )
        if target is None:
            return None
        app = Application(backend="uia").connect(handle=target.handle)
        return app.top_window()
    except Exception:
        return None


def _get_response_text(window) -> str:
    """
    Extract current visible response text from Claude Desktop's UIA tree.
    Uses descendants() since Electron does not expose deep children via elem.children().
    Concatenates all Text-type elements, filtering out known UI chrome strings.
    """
    try:
        descs = window.descendants(control_type="Text")
        parts = []
        for d in descs:
            try:
                t = d.window_text().strip()
                if t and t not in _UI_NOISE and len(t) > 1:
                    parts.append(t)
            except Exception:
                continue
        return " ".join(parts)
    except Exception:
        return ""


class SentenceBuffer:
    def __init__(self):
        self._prev = ""
        self._partial = ""
        self._in_fence = False

    def reset(self):
        self._prev = ""
        self._partial = ""
        self._in_fence = False

    def feed(self, current_text: str) -> list[str]:
        """Feed current full text; returns list of new speakable sentences."""
        if not current_text.startswith(self._prev):
            # Text changed in a non-additive way (new conversation) — reset
            self.reset()

        new_chunk = current_text[len(self._prev):]
        self._prev = current_text

        if not new_chunk:
            return []

        # Track triple-backtick fences — don't speak code
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
            buf.reset()
            prev_text = ""
            continue

        try:
            current_text = _get_response_text(window)
        except Exception:
            current_text = ""

        if current_text != prev_text:
            sentences = buf.feed(current_text)
            for sentence in sentences:
                speak(sentence)
            prev_text = current_text

        time.sleep(_POLL_INTERVAL)


if __name__ == "__main__":
    main()
