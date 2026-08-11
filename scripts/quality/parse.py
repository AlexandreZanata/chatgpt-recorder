"""Function-range and cyclomatic helpers for size/complexity scanning."""

from __future__ import annotations

import re

BRANCH_RE = re.compile(
    r"""(?x)
    \b(?:if|else\s+if|elif|when|case|catch|for|while|do)\b
    | \?
    | &&
    | \|\|
    """
)

FUN_START_RE = re.compile(
    r"""(?x)
    ^[ \t]*
    (?:
        (?:(?:public|private|protected|internal|open|override|suspend|inline|tailrec|fun)\s+)+
        fun\s+
      | (?:async\s+)?function\s+
      | (?:export\s+)?(?:async\s+)?function\s+
      | def\s+
    )
    """
)

METHOD_LIKE_RE = re.compile(
    r"""(?x)
    ^[ \t]*
    (?:
        (?:(?:public|private|protected|internal|open|override|suspend|inline|tailrec|abstract|actual|expect)\s+)*
        fun\s+(?:[`\w.]+\.)?[`\w]+
      | (?:export\s+)?(?:async\s+)?function\s+[\w$]+
      | def\s+[\w]+
      | (?:export\s+)?(?:const|let|var)\s+[\w$]+\s*=\s*(?:async\s*)?\(
    )
    """
)


def strip_strings_and_comments(text: str, suffix: str) -> str:
    if suffix == ".py":
        text = re.sub(r'"""[\s\S]*?"""', '""', text)
        text = re.sub(r"'''[\s\S]*?'''", "''", text)
        text = re.sub(r"#.*", "", text)
        text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
        text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        return text

    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"`(?:\\.|[^`\\])*`", "``", text)
    text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    return text


def find_matching_brace(lines: list[str], start_idx: int) -> int | None:
    depth = 0
    started = False
    for i in range(start_idx, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return i
    return None


def py_function_ranges(lines: list[str]) -> list[tuple[str, int, int]]:
    ranges: list[tuple[str, int, int]] = []
    i = 0
    while i < len(lines):
        match = re.match(r"^([ \t]*)def[ \t]+([\w]+)\s*\(", lines[i])
        if not match:
            i += 1
            continue
        indent = len(match.group(1).expandtabs(4))
        name = match.group(2)
        start = i
        j = i + 1
        while j < len(lines):
            raw = lines[j]
            if raw.strip() == "":
                j += 1
                continue
            stripped = raw.lstrip(" \t")
            cur_indent = len(raw[: len(raw) - len(stripped)].expandtabs(4))
            if cur_indent <= indent and not raw.strip().startswith("#"):
                break
            j += 1
        ranges.append((name, start, j - 1))
        i = j
    return ranges


def c_like_function_ranges(lines: list[str]) -> list[tuple[str, int, int]]:
    ranges: list[tuple[str, int, int]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not METHOD_LIKE_RE.search(line) and not FUN_START_RE.search(line):
            i += 1
            continue
        window = "\n".join(lines[i : min(i + 8, len(lines))])
        if "{" not in window:
            i += 1
            continue
        name_match = re.search(
            r"(?:fun|function|def)\s+(?:[`\w.]+\.)?([`\w]+)", line
        ) or re.search(r"(?:const|let|var)\s+([\w$]+)\s*=", line)
        name = name_match.group(1) if name_match else f"block@{i + 1}"
        brace_line = i
        while brace_line < len(lines) and "{" not in lines[brace_line]:
            brace_line += 1
        if brace_line >= len(lines):
            i += 1
            continue
        end = find_matching_brace(lines, brace_line)
        if end is None:
            i += 1
            continue
        ranges.append((name, i, end))
        i = end + 1
    return ranges


def cyclomatic_for_slice(lines: list[str], suffix: str) -> int:
    text = strip_strings_and_comments("\n".join(lines), suffix)
    return 1 + len(BRANCH_RE.findall(text))
