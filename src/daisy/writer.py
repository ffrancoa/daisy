from pathlib import Path
from rich_click import echo

def write_rust_project(project_name: str, files: dict[str, str]) -> None:
    """
    Create a Rust project directory with the given files.
    `files` is a dict mapping file paths (relative to the project root) to their contents.
    Works for both Leetcode (lib.rs) and DMOJ (main.rs + cli.rs) structures.
    """
    root_dir = Path.cwd() / "exercises" / project_name
    root_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        file_path = root_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
