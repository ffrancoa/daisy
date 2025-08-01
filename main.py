import re
import textwrap
from pathlib import Path

import requests
from bs4 import BeautifulSoup

MAX_WIDTH = 84
OUTPUT_FILENAME = "lib.rs"

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

def extract_problem_parts(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    title = soup.find("h2").text.strip()

    h4_tags = soup.find_all("h4")

    constraints_h4 = next((h for h in h4_tags if h.text.strip() == "Constraints"), None)
    input_h4 = next((h for h in h4_tags if h.text.strip() == "Input Specification"), None)
    output_h4 = next((h for h in h4_tags if h.text.strip() == "Output Specification"), None)
    sample_input_h4 = next((h for h in h4_tags if h.text.strip() == "Sample Input"), None)

    if not input_h4 or not output_h4 or not sample_input_h4:
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
        if tag == sample_input_h4:
            break
        if tag.name == "p":
            output_parts.append(tag.text.strip())

    sample_input = ""
    if sample_input_h4:
        for tag in sample_input_h4.find_next_siblings():
            if tag.name == "pre":
                sample_input = tag.text.strip()
                break

    sample_output = ""
    sample_output_h4 = next((h for h in h4_tags if h.text.strip() == "Sample Output"), None)
    if sample_output_h4:
        for tag in sample_output_h4.find_next_siblings():
            if tag.name == "pre":
                sample_output = tag.text.strip()
                break

    return {
        "title": title,
        "description": "\n\n".join(transform_text(p) for p in description_parts),
        "constraints": "\n\n".join(transform_text(p) for p in constraints_parts) if constraints_parts else None,
        "input_spec": "\n\n".join(transform_text(p) for p in input_parts),
        "output_spec": "\n\n".join(transform_text(p) for p in output_parts),
        "constraints_header": constraints_h4.text.strip() if constraints_h4 else None,
        "input_header": input_h4.text.strip(),
        "output_header": output_h4.text.strip(),
        "sample_input": sample_input,
        "sample_output": sample_output,
    }

def format_problem_comment(data: dict) -> str:
    lines = []
    lines.append(f"// {data['title']}")
    lines.append("//")

    lines.extend([f"// {line}" if line else "//" for line in data["description"].splitlines()])
    lines.append("//")

    if data.get("constraints"):
        lines.append(f"// {data['constraints_header']}")
        lines.append(f"// {'-' * len(data['constraints_header'])}")
        lines.extend([f"// {line}" if line else "//" for line in data["constraints"].splitlines()])
        lines.append("//")

    lines.append(f"// {data['input_header']}")
    lines.append(f"// {'-' * len(data['input_header'])}")
    lines.extend([f"// {line}" if line else "//" for line in data["input_spec"].splitlines()])
    lines.append("//")

    lines.append(f"// {data['output_header']}")
    lines.append(f"// {'-' * len(data['output_header'])}")
    lines.extend([f"// {line}" if line else "//" for line in data["output_spec"].splitlines()])
    lines.append("")

    return "\n".join(lines)

def generate_function_stub(title: str) -> str:
    name = to_snake_case(title)
    return f"pub fn {name}(input: &str) -> String {{\n    todo!(\"pending solution!\")\n}}"

def generate_test_module(function_name: str, sample_input: str, sample_output: str) -> str:
    indented_input = textwrap.indent(sample_input.strip(), " " * 12)
    indented_output = textwrap.indent(sample_output.strip(), " " * 12)

    return f"""\
#[cfg(test)]
mod tests {{
    use super::*;
    use indoc::indoc;

    #[test]
    fn example() {{
        let input = indoc! {{\"
{indented_input}
        \"}};
        let expected = indoc! {{\"
{indented_output}
        \"}};
        assert_eq!({function_name}(input), expected);
    }}
}}"""

def write_to_file(content: str, filename: str = OUTPUT_FILENAME) -> None:
    path = Path(filename)
    path.write_text(content + "\n", encoding="utf-8")
    print(f"Written to {filename}")


def main() -> None:
    url = input("URL> ").strip()
    try:
        data = extract_problem_parts(url)
        comment_block = format_problem_comment(data)
        function_stub = generate_function_stub(data["title"])
        test_module = generate_test_module(
            to_snake_case(data["title"]),
            data["sample_input"],
            data["sample_output"]
        )

        write_to_file(comment_block + "\n" + function_stub + "\n\n" + test_module)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
