import re
import textwrap

from bs4 import BeautifulSoup

MAX_WIDTH = 84

def transform_text(text: str, max_width: int = MAX_WIDTH) -> str:
    def replace_tilde_block(match: re.Match) -> str:
        content = match.group(1)
        content = content.replace(r"\le", "≤").replace(r"\,", " ")
        content = content.replace(r"\ne", "≠").replace(r"\,", " ")
        content = content.replace(r"\times", "×").replace(r"\,", " ")
        content = content.replace(r"\dots", "…")
        content = re.sub(r'(?<!\w)([A-Za-z]\w*)(?!\w)', r'`\1`', content)
        return content

    processed_lines = []
    for raw_line in text.splitlines():
        transformed = re.sub(r"~(.*?)~", replace_tilde_block, raw_line.strip())
        wrapped = textwrap.fill(transformed, width=max_width) if transformed else ""
        processed_lines.append(wrapped)

    return "\n".join(processed_lines)

def to_snake_case(title: str) -> str:
    return re.sub(r"[^\w]+", "_", title.strip().lower()).strip("_")

def extract_clean_title(soup: BeautifulSoup) -> str:
    raw_title = soup.find("h2").text.strip()
    if " - " in raw_title:
        return raw_title.split(" - ", maxsplit=1)[-1].strip()
    return raw_title