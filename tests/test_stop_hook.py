import json
import sys
from io import StringIO
from unittest.mock import patch
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

    # patch.object auto-restores — direct assignment would leak into other test files
    with patch.object(mod.tts, "speak", mock_speak), \
         patch("sys.stdin", StringIO(json.dumps(payload))):
        mod.main()


def test_speaks_last_assistant_message(mocker):
    mock_speak = mocker.MagicMock()
    payload = {
        "last_assistant_message": "Python is a high-level programming language known for its readability."
    }
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_called_once()
    spoken = mock_speak.call_args[0][0]
    assert "Python is a high-level programming language" in spoken


def test_skips_when_no_last_assistant_message(mocker):
    mock_speak = mocker.MagicMock()
    payload = {"session_id": "abc", "last_assistant_message": ""}
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_not_called()


def test_skips_when_key_missing(mocker):
    mock_speak = mocker.MagicMock()
    payload = {"session_id": "abc"}
    _load_and_run_hook(payload, mock_speak)
    mock_speak.assert_not_called()


def test_exits_silently_on_empty_filtered_text(mocker):
    mock_speak = mocker.MagicMock()
    payload = {"last_assistant_message": "```python\nprint('hi')\n```"}
    _load_and_run_hook(payload, mock_speak)
    if mock_speak.called:
        assert mock_speak.call_args[0][0].strip() == ""
