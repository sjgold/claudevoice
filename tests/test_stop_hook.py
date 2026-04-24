import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock
import pytest
import importlib.util
from pathlib import Path


def _load_and_run_hook(payload: dict, mock_speak):
    """Load stop-hook and run main with payload on stdin and mocked speak."""
    if "stop_hook" in sys.modules:
        del sys.modules["stop_hook"]

    spec = importlib.util.spec_from_file_location(
        "stop_hook",
        Path(__file__).parent.parent / "hooks" / "stop-hook.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # After loading, patch the tts module in the loaded module
    mod.tts.speak = mock_speak

    # Run main with payload on stdin
    with patch("sys.stdin", StringIO(json.dumps(payload))):
        mod.main()


def test_speaks_last_assistant_text(mocker):
    mock_speak = mocker.MagicMock()
    payload = {
        "transcript": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language known for its readability."},
        ]
    }
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_called_once()
    spoken = mock_speak.call_args[0][0]
    assert "Python is a high-level programming language" in spoken


def test_skips_when_no_assistant_message(mocker):
    mock_speak = mocker.MagicMock()
    payload = {"transcript": [{"role": "user", "content": "Hello"}]}
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_not_called()


def test_handles_content_block_array(mocker):
    mock_speak = mocker.MagicMock()
    payload = {
        "transcript": [
            {"role": "user", "content": "Show me code"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Here is an explanation of how this works in practice."},
                {"type": "tool_use", "name": "bash", "input": {"command": "ls"}},
            ]},
        ]
    }
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_called_once()
    spoken = mock_speak.call_args[0][0]
    assert "Here is an explanation" in spoken
    assert "bash" not in spoken


def test_exits_silently_on_empty_filtered_text(mocker):
    mock_speak = mocker.MagicMock()
    payload = {
        "transcript": [
            {"role": "user", "content": "Show code"},
            {"role": "assistant", "content": "```python\nprint('hi')\n```"},
        ]
    }
    _load_and_run_hook(payload, mock_speak)
    # speak() called with empty/whitespace-only — tts.speak handles the no-op
    if mock_speak.called:
        assert mock_speak.call_args[0][0].strip() == ""
