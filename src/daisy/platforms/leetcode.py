from urllib.parse import urlparse
import json
import re

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from daisy.utils import format_leetcode_text, group_constraints

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

    return {
        "title": title,
        "description": "\n\n".join(description_parts),
        "constraints": constraints_block,
        "constraints_header": constraints_header,
        "sample_inputs": [],
        "sample_outputs": [],
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
