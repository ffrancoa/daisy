from pathlib import Path

OUTPUT_FILENAME = "lib.rs"

def write_to_file(content: str, filename: str = OUTPUT_FILENAME) -> None:
    path = Path(filename)
    path.write_text(content + "\n", encoding="utf-8")
    print(f"Written to {filename}")