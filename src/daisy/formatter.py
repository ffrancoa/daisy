import textwrap

from daisy.utils import to_snake_case

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

def generate_test_module(function_name: str, sample_inputs: list[str], sample_outputs: list[str]) -> str:
    def normalize_indent(s):
        return "\n".join(line.lstrip() for line in s.splitlines())

    tests = []
    single_example = len(sample_inputs) == 1

    for i, (sample_in, sample_out) in enumerate(zip(sample_inputs, sample_outputs), start=1):
        test_name = "example" if single_example else f"example_{i}"
        indented_input = textwrap.indent(normalize_indent(sample_in.strip()), " " * 12)
        indented_output = textwrap.indent(normalize_indent(sample_out.strip()), " " * 12)
        tests.append(f"""\
    #[test]
    fn {test_name}() {{
        let input = indoc! {{\"
{indented_input}
        \"}};
        let expected = indoc! {{\"
{indented_output}
        \"}};
        assert_eq!({function_name}(input), expected);
    }}""")

    tests_str = "\n\n".join(tests)
    return f"""\
#[cfg(test)]
mod tests {{
    use super::*;
    use indoc::indoc;

{tests_str}
}}"""