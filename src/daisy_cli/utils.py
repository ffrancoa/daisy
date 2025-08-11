import re
import textwrap

from bs4 import BeautifulSoup
from bs4.element import NavigableString

MAX_WIDTH = 84

def format_dmoj_text(text: str, max_width: int = MAX_WIDTH) -> str:
    def _replace_tilde_block(match: re.Match) -> str:
        content = match.group(1)
        content = content.replace(r"\le", "<=").replace(r"\,", " ")
        content = content.replace(r"\ne", "!=").replace(r"\,", " ")
        content = content.replace(r"\times", "×").replace(r"\,", " ")
        content = content.replace(r"\dots", "…")
        content = re.sub(r'(?<!\w)([A-Za-z]\w*)(?!\w)', r'`\1`', content)
        return content
    
    processed_lines = []

    for raw_line in text.splitlines():
        transformed = re.sub(r"~(.*?)~", _replace_tilde_block, raw_line.strip())
        wrapped = textwrap.fill(transformed, width=max_width) if transformed else ""
        processed_lines.append(wrapped)

    return "\n".join(processed_lines)

def format_leetcode_text(html: str, max_width: int = MAX_WIDTH) -> str:
    """
    Format small HTML snippets coming from LeetCode:
    - convert <sup>n</sup> -> ^n (without spaces)
    - replace <=, &lt;=, >=, &gt;= -> ≤ / ≥ and ensure spaces around them
    - for <code>...</code> content, wrap only identifier-like tokens
      (allowing dotted identifiers, e.g. nums.length) in backticks
    - normalize whitespace and line-wrap to max_width
    """
    soup = BeautifulSoup(html, "lxml")

    # 1) Convert <sup>n</sup> -> ^n (as NavigableString)
    for sup in soup.find_all("sup"):
        sup.replace_with(NavigableString(f"^{sup.get_text(strip=True)}"))

    def _process_code_content(s: str) -> str:
        s = re.sub(r"\s*\^\s*", "^", s)

        ident_pattern = re.compile(r"""
            (?<!\w)                                     # no word char before
            ([A-Za-z]\w*(?:\[[^\]]+\]|\.[A-Za-z]\w*)*)  # base identifier
            (\^[A-Za-z]\w*)?                            # optional exponent
            (?!\w)                                      # no word char after
        """, re.VERBOSE)

        # only wrap the base in backticks, leave exponent raw
        s = ident_pattern.sub(lambda m: f"`{m.group(1)}`{m.group(2) or ''}", s)

        return re.sub(r"\s+", " ", s).strip()

    for code_tag in soup.find_all("code"):
        processed = _process_code_content(code_tag.get_text())
        code_tag.replace_with(NavigableString(processed))

    text = soup.get_text()

    # ensure spaces around ≤/≥ globally (just in case)
    text = re.sub(r"\s*≤\s*", " ≤ ", text)
    text = re.sub(r"\s*≥\s*", " ≥ ", text)

    # remove stray spaces before ^ and normalize spaces
    text = re.sub(r"\s+\^", "^", text)
    text = re.sub(r"\s+", " ", text).strip()

    processed_lines = []
    for raw_line in text.splitlines():
        if raw_line.strip():
            wrapped = textwrap.fill(raw_line.strip(), width=max_width)
        else:
            wrapped = ""
        processed_lines.append(wrapped)

    return "\n".join(processed_lines)

def is_math_constraint(line: str) -> bool:
    """Return True if the constraint looks like a mathematical expression."""
    return bool(re.search(r"(≤|≥|<|>|=|\^\d|\d)", line))

def group_constraints(constraints: list[str]) -> str:
    """
    Join constraints so that:
      - Math constraints are grouped without blank lines.
      - Exactly one blank line before the first textual constraint.
    """
    processed = []
    last_was_math = None

    for line in constraints:
        line = line.strip()
        if not line:
            continue  # skip accidental empties

        if is_math_constraint(line):
            if last_was_math is False:  # coming from text → math
                processed.append("")  # keep separation from previous text
            processed.append(line)
            last_was_math = True
        else:
            if last_was_math:  # coming from math → text
                processed.append("")  # exactly one blank line before text
            processed.append(line)
            last_was_math = False

    return "\n".join(processed)

def to_snake_case(title: str) -> str:
    return re.sub(r"[^\w]+", "_", title.strip().lower()).strip("_")

def extract_clean_title(soup: BeautifulSoup) -> str:
    h2_tag = soup.find("h2")
    if h2_tag is None:
        raise ValueError("No <h2> element found in the HTML content.")

    raw_title = h2_tag.get_text(strip=True)
    if " - " in raw_title:
        return raw_title.split(" - ", maxsplit=1)[-1].strip()
    return raw_title
