import rich_click as click
from urllib.parse import urlparse

from daisy.platforms import dmoj
from daisy import formatter, writer

SCRAPERS = {
    "dmoj.ca": dmoj.extract_problem_parts,
    # future: "leetcode.com": leetcode.extract_problem_parts,
    # future: "codeforces.com": codeforces.extract_problem_parts,
}

@click.group()
def cli():
    """A Python CLI that scrapes coding sites to craft Rust problem templates."""
    pass

@cli.command(name="url")
@click.argument("url")
def url_cmd(url: str):
    """Generate template from problem URL."""
    domain = urlparse(url).netloc
    scraper = next((fn for host, fn in SCRAPERS.items() if host in domain), None)

    if not scraper:
        click.echo(f"Unsupported site: {domain}")
        return

    try:
        data = scraper(url)
        comment_block = formatter.format_problem_comment(data)
        function_stub = formatter.generate_function_stub(data["title"])
        test_module = formatter.generate_test_module(
            formatter.to_snake_case(data["title"]),
            data["sample_inputs"],
            data["sample_outputs"]
        )
        lib_content = comment_block + "\n" + function_stub + "\n\n" + test_module
        project_name = formatter.to_snake_case(data["title"])
        writer.write_rust_project(project_name, lib_content)
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    cli()
