import rich_click as click
from urllib.parse import urlparse

from daisy.platforms import dmoj
from daisy.formatter import render_rust_template
from daisy.utils import to_snake_case
from daisy.writer import write_rust_project

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
        lib_content = render_rust_template(data)
        project_name = to_snake_case(data["title"])
        write_rust_project(project_name, lib_content)
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    cli()
