from urllib.parse import urlparse
import json
import re

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from daisy_cli.utils import format_leetcode_text, group_constraints

GRAPHQL_URL = "https://leetcode.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
}

def extract_problem_parts(url: str) -> dict:
    def _slug_from_url(url: str) -> str:
        """
        Extracts the problem slug from a LeetCode URL.
        """
        path_parts = urlparse(url).path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "problems":
            return path_parts[1]
        raise ValueError(f"Invalid LeetCode problem URL: {url}")

    slug = _slug_from_url(url)

    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        title
        content
        codeDefinition
        sampleTestCase
        exampleTestcases
      }
    }
    """
    variables = {"titleSlug": slug}

    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    response.raise_for_status()
    data = response.json()

    question = data.get("data", {}).get("question")
    if not question:
        raise ValueError(f"Could not retrieve question for slug '{slug}'")

    title = question["title"]

    soup = BeautifulSoup(question["content"], "lxml")
    paragraphs = soup.find_all("p")

    # detect end of description (empty paragraph separator)
    desc_end_idx = None
    for i, p in enumerate(paragraphs):
        if not p.get_text(strip=True):
            desc_end_idx = i
            break

    if desc_end_idx is None:
        desc_end_idx = len(paragraphs)

    description_parts = [
        format_leetcode_text(str(p)) for p in paragraphs[:desc_end_idx]
    ]

    constraints_header = None
    constraints_parts = []

    constraints_p = soup.find(
        "p",
        string=lambda t: bool(t and t.strip().startswith("Constraints:"))
    )

    if constraints_p:
        constraints_header = constraints_p.get_text(strip=True).rstrip(":")
        ul_tag = constraints_p.find_next_sibling("ul")
        if isinstance(ul_tag, Tag):
            for li in ul_tag.find_all("li"):
                constraints_parts.append(format_leetcode_text(str(li)))

    constraints_block = group_constraints(constraints_parts) if constraints_parts else None
    rust_signature = extract_rust_signature(question.get("codeDefinition", ""))
    sample_inputs, sample_outputs, sample_explanations, varnames = extract_samples(soup)

    return {
        "title": title,
        "description": "\n\n".join(description_parts),
        "constraints": constraints_block,
        "constraints_header": constraints_header,
        "sample_inputs": sample_inputs,
        "sample_outputs": sample_outputs,
        "sample_explanations": sample_explanations,
        "sample_varnames": varnames,
        "rust_signature": rust_signature,
    }

def extract_rust_signature(code_definition_json: str) -> str | None:
    """
    Extracts only the Rust function signature from LeetCode's codeDefinition JSON.
    """
    try:
        code_defs = json.loads(code_definition_json)
    except json.JSONDecodeError:
        return None

    rust_entry = next((entry for entry in code_defs if entry.get("value") == "rust"), None)
    if not rust_entry:
        return None

    default_code = rust_entry.get("defaultCode", "")

    matched = re.search(
        r"(pub\s+fn\s+[^(]+\([^)]*\)\s*->\s*[^{]+\{\s*\})",
        default_code,
        re.S
    )
    if matched:
        code_snippet = matched.group(1).strip()
        lines = code_snippet.strip().splitlines()
        return lines[0]
    return None

def extract_samples(soup: BeautifulSoup) -> tuple[list[str], list[str], list[str], list[list[str]]]:
    """
    Parse LeetCode <pre> example blocks and produce Rust-ready
    `sample_inputs` (multi-line let-statements) and `sample_outputs`.
    This is generic: it discovers `name = value` pairs and maps:
      - bracketed lists -> `vec![...]` (elements normalized with ", ")
      - scalars left as-is
    """
    def _split_top_level_commas(s: str) -> list[str]:
        parts = []
        buf = []
        depth = 0
        in_quote = None
        for ch in s:
            if in_quote:
                buf.append(ch)
                if ch == in_quote:
                    in_quote = None
                continue
            if ch in ("'", '"'):
                in_quote = ch
                buf.append(ch)
                continue
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
            if ch == ',' and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf).strip())
        return parts

    def _parse_assignments(s: str) -> list[tuple[str, str]]:
        """
        Returns list of (name, raw_value) preserving order.
        Handles values that are bracketed lists (with nested brackets)
        or simple scalars separated by top-level commas.
        """
        i = 0
        n = len(s)
        assignments = []
        while i < n:
            # skip whitespace
            while i < n and s[i].isspace():
                i += 1
            # name
            m = re.match(r"[A-Za-z_]\w*", s[i:])
            if not m:
                break
            name = m.group(0)
            i += m.end()
            # skip spaces and equals
            while i < n and s[i].isspace():
                i += 1
            if i >= n or s[i] != "=":
                break
            i += 1
            # skip spaces
            while i < n and s[i].isspace():
                i += 1
            # value
            if i < n and s[i] == "[":
                start = i
                depth = 0
                in_quote = None
                while i < n:
                    ch = s[i]
                    if in_quote:
                        if ch == in_quote:
                            in_quote = None
                    else:
                        if ch in ('"', "'"):
                            in_quote = ch
                        elif ch == "[":
                            depth += 1
                        elif ch == "]":
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                    i += 1
                raw_value = s[start:i].strip()
            else:
                start = i
                # scalar until top-level comma
                while i < n and s[i] != ",":
                    i += 1
                raw_value = s[start:i].strip()
            assignments.append((name, raw_value))
            # skip comma if present
            while i < n and s[i].isspace():
                i += 1
            if i < n and s[i] == ",":
                i += 1
        return assignments

    def _to_rust_value(raw: str) -> str:
        raw = raw.strip()
        # list-ish
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            if inner == "":
                return "vec![]"
            elems = _split_top_level_commas(inner)
            norm_elems = []
            for e in elems:
                e = e.strip()
                # keep strings as-is, but normalize quotes to double quotes if single quoted
                if (e.startswith("'") and e.endswith("'")):
                    e = '"' + e[1:-1].replace('"', '\\"') + '"'
                norm_elems.append(e)
            return "vec![" + ", ".join(norm_elems) + "]"
        # quoted string
        if (raw.startswith("'") and raw.endswith("'")):
            return '"' + raw[1:-1].replace('"', '\\"') + '"'
        # numeric?
        if re.fullmatch(r"-?\d+(\.\d+)?", raw):
            return raw
        # boolean (lowercase)
        if raw.lower() in ("true", "false"):
            return raw.lower()
        # fallback: return as-is (caller may handle)
        return raw

    sample_inputs: list[str]  = []
    sample_outputs: list[str]  = []
    sample_explanations: list[str]  = []
    sample_varnames: list[list[str]] = []

    for pre in soup.find_all("pre"):
        text = pre.get_text("\n", strip=True)
        input_m = re.search(r"Input:\s*(.+)", text)
        output_m = re.search(r"Output:\s*(.+)", text)
        explanation_match = re.search(r"Explanation:\s*(.+)", text)
        if not input_m or not output_m:
            continue

        input_str = input_m.group(1).strip()
        output_str = output_m.group(1).strip()
        explanation_str = explanation_match.group(1).strip() if explanation_match else ""

        assignments = _parse_assignments(input_str)
        if not assignments:
            continue

        input_lines = []
        varnames = []
        for name, raw_val in assignments:
            rust_val = _to_rust_value(raw_val)
            input_lines.append(f"let {name} = {rust_val};")
            varnames.append(name)

        sample_inputs.append("\n".join(input_lines))
        sample_varnames.append(varnames)

        expected_val = _to_rust_value(output_str)
        sample_outputs.append(expected_val)

        sample_explanations.append(explanation_str)

    return sample_inputs, sample_outputs, sample_explanations, sample_varnames
