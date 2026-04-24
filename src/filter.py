import re

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_TOOL_BLOCK = re.compile(r"<tool_(?:use|result)>[\s\S]*?</tool_(?:use|result)>", re.DOTALL)
_MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_HORIZONTAL_RULE = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)
_LIST_ITEM = re.compile(r"^(\s*(?:[-*]|\d+\.)\s+.+)$", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_VERBOSITY_LIMITS = {"low": 1, "medium": 5, "high": float("inf")}


def _apply_verbosity(text: str, verbosity: str) -> str:
    limit = _VERBOSITY_LIMITS.get(verbosity, 2)
    if limit == float("inf"):
        return text

    lines = text.splitlines(keepends=True)
    result = []
    list_items = []
    in_list = False

    def flush_list():
        if not list_items:
            return
        # Don't truncate if list is short (3 or fewer items)
        if len(list_items) <= 3:
            result.extend(list_items)
        else:
            kept = list_items[:int(limit)]
            remaining = len(list_items) - len(kept)
            result.extend(kept)
            if remaining > 0:
                result.append(f"  ... and {remaining} more point{'s' if remaining > 1 else ''}.\n")

    for line in lines:
        if _LIST_ITEM.match(line):
            in_list = True
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


def filter_response(text: str, verbosity: str = "low") -> str:
    text = _CODE_FENCE.sub("", text)
    text = _TOOL_BLOCK.sub("", text)
    text = _INLINE_CODE.sub("", text)
    text = _MARKDOWN_HEADER.sub("", text)
    text = _HORIZONTAL_RULE.sub("", text)
    text = _apply_verbosity(text, verbosity)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_prose_sentences(text: str, verbosity: str = "low") -> list[str]:
    filtered = filter_response(text, verbosity=verbosity)
    parts = _SENTENCE_SPLIT.split(filtered)
    return [s.strip() for s in parts if len(s.split()) >= 4]
