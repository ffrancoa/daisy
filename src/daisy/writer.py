from pathlib import Path

from rich_click import echo

OUTPUT_FILENAME = "lib.rs"

def write_to_file(content: str, filename: str = OUTPUT_FILENAME) -> None:
    path = Path(filename)
    path.write_text(content + "\n", encoding="utf-8")
    echo(f"ok: written to '{filename}'")