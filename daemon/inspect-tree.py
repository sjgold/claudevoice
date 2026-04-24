#!/usr/bin/env python
"""
Run once with Claude Desktop open to discover the accessibility tree structure.
Output shows control types, names, and text content so we can find the right selectors.
Usage: python daemon/inspect-tree.py > daemon/tree-dump.txt
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


def dump_element(elem, depth=0, max_depth=12):
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
    print("Looking for Claude Desktop window...", file=sys.stderr)
    try:
        desktop = Desktop(backend="uia")
        # List all matching windows to help diagnose
        all_windows = desktop.windows()
        claude_windows = [w for w in all_windows if "claude" in w.window_text().lower()]
        print(f"Found {len(claude_windows)} Claude-related windows:", file=sys.stderr)
        for w in claude_windows:
            print(f"  title={w.window_text()!r}  class={w.class_name()!r}", file=sys.stderr)

        # Prefer exact title "Claude" (Claude Desktop), then fall back to Chrome_WidgetWin_1
        target = next((w for w in claude_windows if w.window_text().strip() == "Claude"), None)
        if target is None:
            target = next(
                (w for w in claude_windows if w.class_name() == "Chrome_WidgetWin_1"),
                None
            )
        if target is None:
            print("Could not identify Claude Desktop window.", file=sys.stderr)
            sys.exit(1)

        print(f"Dumping: {target.window_text()!r}", file=sys.stderr)
        app = Application(backend="uia").connect(handle=target.handle)
        window = app.top_window()
        dump_element(window.wrapper_object())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
