import requests
from bs4 import BeautifulSoup

from daisy_cli.utils import extract_clean_title, format_dmoj_text

def extract_problem_parts(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    title = extract_clean_title(soup)

    h4_tags = soup.find_all("h4")

    constraints_h4 = next((h for h in h4_tags if h.text.strip() == "Constraints"), None)
    input_h4 = next((h for h in h4_tags if h.text.strip() == "Input Specification"), None)
    output_h4 = next((h for h in h4_tags if h.text.strip() == "Output Specification"), None)

    if not input_h4 or not output_h4:
        raise ValueError("Could not find all required section headers.")

    first_h4 = h4_tags[0]

    description_parts = []
    for tag in first_h4.find_all_previous():
        if tag.name == "h2":
            break
        if tag.name == "p":
            description_parts.insert(0, tag.text.strip())

    constraints_parts = []
    if constraints_h4:
        for tag in constraints_h4.find_next_siblings():
            if tag == input_h4:
                break
            if tag.name == "p":
                constraints_parts.append(tag.text.strip())

    input_parts = []
    for tag in input_h4.find_next_siblings():
        if tag == output_h4:
            break
        if tag.name == "p":
            input_parts.append(tag.text.strip())

    output_parts = []
    for tag in output_h4.find_next_siblings():
        if tag.name == "h4" and tag.text.strip().startswith("Sample Input"):
            break
        if tag.name == "p":
            output_parts.append(tag.text.strip())

    sample_inputs = []
    for h in h4_tags:
        if h.text.strip().startswith("Sample Input"):
            for tag in h.find_next_siblings():
                if tag.name == "pre":
                    sample_inputs.append(tag.text.strip())
                    break

    sample_outputs = []
    for h in h4_tags:
        if h.text.strip().startswith("Sample Output"):
            for tag in h.find_next_siblings():
                if tag.name == "pre":
                    sample_outputs.append(tag.text.strip())
                    break

    return {
        "title": title,
        "description": "\n\n".join(format_dmoj_text(p) for p in description_parts),
        "constraints": "\n\n".join(format_dmoj_text(p) for p in constraints_parts) if constraints_parts else None,
        "input_spec": "\n\n".join(format_dmoj_text(p) for p in input_parts),
        "output_spec": "\n\n".join(format_dmoj_text(p) for p in output_parts),
        "constraints_header": constraints_h4.text.strip() if constraints_h4 else None,
        "input_header": input_h4.text.strip(),
        "output_header": output_h4.text.strip(),
        "sample_inputs": sample_inputs,
        "sample_outputs": sample_outputs,
    }