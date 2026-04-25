import re

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_TOOL_BLOCK = re.compile(r"<tool_(?:use|result)>[\s\S]*?</tool_(?:use|result)>", re.DOTALL)
_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_HORIZONTAL_RULE = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)
_LIST_ITEM = re.compile(r"^(\s*(?:[-*]|\d+\.)\s+.+)$", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_SENTENCE_CAPS = {"1": 1, "2": 2}


def _apply_verbosity(text: str, verbosity: str) -> str:
    if verbosity not in ("1", "2", "3", "4"):
        raise ValueError(f"Invalid verbosity: {verbosity!r}. Use 1, 2, 3, or 4.")
    if verbosity in ("3", "4"):
        return text

    limit = 0 if verbosity == "1" else 3

    lines = text.splitlines(keepends=True)
    result = []
    list_items = []
    in_list = False

    def flush_list():
        total = len(list_items)
        if verbosity == "1":
            result.append(f"[{total} item{'s' if total != 1 else ''} not read aloud].\n")
            return
        kept = list_items[:limit]
        remaining = total - len(kept)
        result.extend(kept)
        if remaining > 0:
            result.append(f"  ... and {remaining} more.\n")

    for line in lines:
        if _LIST_ITEM.match(line):
            in_list = True
            list_items.append(line)
        elif in_list and not line.strip():
            list_items.append(line)
        else:
            if in_list:
                flush_list()
                list_items = []
                in_list = False
            result.append(line)

    if in_list:
        flush_list()

    return "".join(result)


def filter_response(text: str, verbosity: str = "2") -> str:
    if not isinstance(text, str):
        return ""
    # Normalize Windows line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CODE_FENCE.sub("", text)
    # Strip from any remaining unclosed ``` to end of string (Claude never puts prose after an unclosed fence)
    text = re.sub(r"```.*", "", text, flags=re.DOTALL)
    text = _TOOL_BLOCK.sub("", text)
    text = _INLINE_CODE.sub("", text)
    text = _MARKDOWN_HEADER.sub("", text)
    text = _HORIZONTAL_RULE.sub("", text)
    text = _apply_verbosity(text, verbosity)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    cap = _SENTENCE_CAPS.get(verbosity)
    if cap:
        parts = _SENTENCE_SPLIT.split(text)
        if len(parts) > cap:
            text = " ".join(p.strip() for p in parts[:cap])
            if not text.endswith((".", "!", "?")):
                text += "."
    return text


def extract_prose_sentences(text: str, verbosity: str = "2") -> list[str]:
    filtered = filter_response(text, verbosity=verbosity)
    parts = _SENTENCE_SPLIT.split(filtered)
    return [s.strip() for s in parts if len(s.split()) >= 4]
