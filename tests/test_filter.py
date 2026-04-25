import pytest
from src.filter import filter_response, extract_prose_sentences


def test_strips_triple_backtick_fence():
    text = "Here is the answer.\n```python\nprint('hello')\n```\nThat is the code."
    result = filter_response(text)
    assert "print" not in result
    assert "Here is the answer." in result
    assert "That is the code." in result


def test_strips_inline_code():
    text = "Use the `ffplay` command to play audio files."
    result = filter_response(text)
    assert "`ffplay`" not in result
    assert "Use the" in result
    assert "command to play audio files." in result


def test_strips_tool_call_blocks():
    text = "Let me check that.\n<tool_use>\n{\"name\": \"bash\"}\n</tool_use>\nDone checking."
    result = filter_response(text)
    assert "tool_use" not in result
    assert "Let me check that." in result
    assert "Done checking." in result


def test_strips_diff_blocks():
    text = "I made a change.\n```diff\n- old line\n+ new line\n```\nAll done."
    result = filter_response(text)
    assert "- old line" not in result
    assert "I made a change." in result
    assert "All done." in result


def test_pure_code_response_returns_empty():
    text = "```python\ndef foo():\n    return 42\n```"
    result = filter_response(text)
    assert result.strip() == ""


def test_plain_prose_passes_through():
    text = "That is a great question. The answer depends on context."
    result = filter_response(text)
    assert "That is a great question." in result
    assert "The answer depends on context." in result


def test_extract_sentences_filters_short():
    text = "Yes. That is an interesting approach to the problem. No. Absolutely."
    sentences = extract_prose_sentences(text)
    assert all(len(s.split()) >= 4 for s in sentences)


def test_extract_sentences_handles_question_and_exclamation():
    text = "Is this the right approach? It definitely seems correct! Let me explain why."
    sentences = extract_prose_sentences(text)
    assert len(sentences) == 3


def test_low_verbosity_replaces_list_with_summary():
    text = "Here are the steps:\n- First do this\n- Then do that\n- Also this\n- And this too\n- Finally this"
    result = filter_response(text, verbosity="1")
    assert "First do this" not in result
    assert "The response included a list of 5 items." in result


def test_low_verbosity_replaces_short_list_too():
    text = "Two options:\n- Option A\n- Option B"
    result = filter_response(text, verbosity="1")
    assert "Option A" not in result
    assert "The response included a list of 2 items." in result


def test_medium_verbosity_keeps_three_bullets():
    items = "\n".join(f"- Item {i}" for i in range(1, 7))
    text = f"The list:\n{items}"
    result = filter_response(text, verbosity="2")
    assert "Item 1" in result
    assert "Item 3" in result
    assert "Item 4" not in result
    assert "3 more" in result


def test_high_verbosity_reads_all_bullets():
    items = "\n".join(f"- Item {i}" for i in range(1, 9))
    text = f"Full list:\n{items}"
    result = filter_response(text, verbosity="3")
    assert "Item 8" in result


def test_markdown_headers_stripped():
    text = "## Architecture\n\nThis is the main explanation of the architecture."
    result = filter_response(text)
    assert "##" not in result
    assert "This is the main explanation" in result


def test_strips_horizontal_rules():
    text = "First point.\n\n---\n\nSecond point here."
    result = filter_response(text)
    assert "---" not in result
    assert "First point." in result
    assert "Second point here." in result


def test_filter_response_handles_none_input():
    result = filter_response(None)
    assert result == ""


def test_filter_response_normalizes_windows_line_endings():
    text = "Hello world.\r\n- Item one\r\n- Item two\r\nDone."
    result = filter_response(text, verbosity="3")
    assert "\r" not in result


def test_unclosed_code_fence_does_not_leak():
    text = "Here is some code:\n```python\ndef foo():\n    pass"
    result = filter_response(text)
    assert "def foo" not in result



def test_filter_response_rejects_invalid_verbosity():
    with pytest.raises(ValueError):
        filter_response("some text", verbosity="extreme")
