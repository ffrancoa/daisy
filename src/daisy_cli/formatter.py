import textwrap
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from daisy_cli.utils import to_snake_case

INDOC_VERSION       = "2.0.6"
DMOJ_VERSION        = "0.1.5"
ASSERT_CMD_VERSION  = "2.0.17"

TEMPLATES_DIR = Path(__file__).parent / "templates"

def format_samples(inputs: list[str], outputs: list[str], explanations: list[str], varnames: list[list[str]]) -> list[dict]:
    def _normalize_indent(s):
        return "\n".join(line.lstrip() for line in s.splitlines())
    return [
        {
            "name": "example" if len(inputs) == 1 else f"example_{i+1}",
            "input": _normalize_indent(inn.strip()),
            "output": _normalize_indent(out.strip()),
            "explanation": (
                textwrap.fill(
                    _normalize_indent(explanations[i].strip()),
                    width=77  # max width = 88 - 9
                ) if i < len(explanations) and explanations[i] else ""
            ),
            "varnames": varnames[i] if i < len(varnames) else []
        }
        for i, (inn, out) in enumerate(zip(inputs, outputs))
    ]

def render_rust_template(data: dict, source: str) -> dict:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR / source),
        trim_blocks=True,
        lstrip_blocks=True
    )

    fn_name = to_snake_case(data["title"])

    if data.get("rust_signature"):
        parts = data["rust_signature"].strip().split()
        if len(parts) >= 3:
            fn_name = parts[2].split("(")[0]

    samples = format_samples(
        data.get("sample_inputs", []),
        data.get("sample_outputs", []),
        data.get("sample_explanations", []),
        data.get("sample_varnames", [])
    )

    if source == "leetcode":
        return {
            "src/lib.rs": env.get_template("lib.rs.j2").render(
                title=data["title"],
                description=data["description"],
                constraints=data.get("constraints"),
                constraints_header=data.get("constraints_header", ""),
                input_header=data.get("input_header", ""),
                input_spec=data.get("input_spec", ""),
                output_header=data.get("output_header", ""),
                output_spec=data.get("output_spec", ""),
                function_name=fn_name,
                rust_signature=data.get("rust_signature"),
                use_indoc=data.get("rust_signature") is None,
                samples=samples,
            ),
            "Cargo.toml": env.get_template("Cargo.toml.j2").render(
                name=to_snake_case(data["title"])
            )
        }
    elif source == "dmoj":
        return {
            "src/main.rs": env.get_template("main.rs.j2").render(
                title=data["title"],
                description=data["description"],
                constraints=data.get("constraints"),
                constraints_header=data.get("constraints_header", ""),
                input_header=data.get("input_header", ""),
                input_spec=data.get("input_spec", ""),
                output_header=data.get("output_header", ""),
                output_spec=data.get("output_spec", ""),
            ),
            "tests/cli.rs": env.get_template("cli.rs.j2").render(
                name=to_snake_case(data["title"]),
                samples=samples
            ),
            "Cargo.toml": env.get_template("Cargo.toml.j2").render(
                name=to_snake_case(data["title"]),
                indoc_version=INDOC_VERSION,
                dmoj_version=DMOJ_VERSION,
                assert_cmd_version=ASSERT_CMD_VERSION
            )
        }
    else:
        raise ValueError(f"Unknown source: {source}")
