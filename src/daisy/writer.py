from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich_click import echo

OUTPUT_FILENAME = "lib.rs"
INDOC_VERSION = "2.0.6"

TEMPLATES_DIR = Path(__file__).parent / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(disabled_extensions=("toml", "rs", "txt")),
)

def write_rust_project(project_name: str, lib_content: str, use_indoc: bool) -> None:
    """
    Create a minimal Rust project with the given name and lib.rs content.
    """
    root_dir = Path.cwd() / "exercises" / project_name
    src_dir = root_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    lib_path = src_dir / "lib.rs"
    lib_path.write_text(lib_content.strip() + "\n", encoding="utf-8")

    cargo_template = jinja_env.get_template("Cargo.toml.j2")
    rendered_toml = cargo_template.render(
        name=project_name,
        indoc_version=INDOC_VERSION,
        use_indoc=use_indoc,
    )

    (root_dir / "Cargo.toml").write_text(rendered_toml, encoding="utf-8")

    echo(f"ok: project created at '{root_dir}'")