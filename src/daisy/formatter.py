import textwrap
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from daisy.utils import to_snake_case

TEMPLATES_DIR = Path(__file__).parent / "templates"

def normalize_indent(s):
    return "\n".join(line.lstrip() for line in s.splitlines())

def format_samples(inputs: list[str], outputs: list[str], explanations: list[str]) -> list[dict]:
    return [
        {
            "name": "example" if len(inputs) == 1 else f"example_{i+1}",
            "input": normalize_indent(inn.strip()),
            "output": normalize_indent(out.strip()),
            "explanation": (
                textwrap.fill(
                    normalize_indent(explanations[i].strip()),
                    width=77  # max width = 88
                ) if i < len(explanations) and explanations[i] else ""
            )
        }
        for i, (inn, out) in enumerate(zip(inputs, outputs))
    ]


def render_rust_template(data: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("lib.rs.j2")

    return template.render(
        title=data["title"],
        description=data["description"],
        constraints=data.get("constraints"),
        constraints_header=data.get("constraints_header", ""),
        input_header=data.get("input_header", ""),
        input_spec=data.get("input_spec", ""),
        output_header=data.get("output_header", ""),
        output_spec=data.get("output_spec", ""),
        function_name=to_snake_case(data["title"]),
        rust_signature=data.get("rust_signature"),
        use_indoc = data.get("rust_signature") is None,
        samples=format_samples(
            data.get("sample_inputs", []),
            data.get("sample_outputs", []),
            data.get("sample_explanations", [])
        ),
    )
