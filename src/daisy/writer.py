from pathlib import Path

from rich_click import echo

OUTPUT_FILENAME = "lib.rs"
INDOC_VERSION = "2.0.6"

def write_to_file(content: str, filename: str = OUTPUT_FILENAME) -> None:
    path = Path(filename)
    path.write_text(content + "\n", encoding="utf-8")
    echo(f"ok: written to '{filename}'")

def write_rust_project(project_name: str, lib_content: str) -> None:
    """
    Create a minimal Rust project with the given name and lib.rs content.
    """
    root_dir = Path(project_name)
    src_dir  = root_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    lib_path = src_dir / "lib.rs"
    lib_path.write_text(lib_content.strip() + "\n", encoding="utf-8")

    cargo_toml_content = f"""\
[package]
name = "{project_name}"
version = "0.1.0"
edition = "2024"

[lints.rust]
unused_variables = "allow"

[dependencies]
indoc = {{ version = "{INDOC_VERSION}" }}
"""
    
    (root_dir / "Cargo.toml").write_text(cargo_toml_content, encoding="utf-8")

    echo(f"ok: project created at '{root_dir}'")