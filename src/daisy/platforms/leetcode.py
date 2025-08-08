from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from daisy.utils import format_leetcode_text, group_constraints

GRAPHQL_URL = "https://leetcode.com/graphql"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
}

def _slug_from_url(url: str) -> str:
    """
    Extracts the problem slug from a LeetCode URL.
    """
    path_parts = urlparse(url).path.strip("/").split("/")
    if len(path_parts) >= 2 and path_parts[0] == "problems":
        return path_parts[1]
    raise ValueError(f"Invalid LeetCode problem URL: {url}")

def extract_problem_parts(url: str) -> dict:
    slug = _slug_from_url(url)

    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        title
        content
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

    # Detect end of description (empty paragraph separator)
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

    return {
        "title": title,
        "description": "\n\n".join(description_parts),
        "constraints": constraints_block,
        "constraints_header": constraints_header,
        "sample_inputs": [],
        "sample_outputs": [],
    }
