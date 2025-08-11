import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import rich_click as click
from rich.console import Console

from daisy_cli.formatter import render_rust_template
from daisy_cli.platforms import dmoj, leetcode
from daisy_cli.utils import to_snake_case
from daisy_cli.writer import write_rust_project

SCRAPERS = {
    "dmoj.ca": dmoj.extract_problem_parts,
    "leetcode.com": leetcode.extract_problem_parts,
}
EXERCISES_DIR = Path("exercises")
PROGRESS_FILE = EXERCISES_DIR / ".daisy_progress.json"

console = Console()


class TestRunner:
    """Handles running and parsing cargo tests."""
    
    def __init__(self, project_dir: Path, verbose: bool = False):
        self.project_dir = project_dir
        self.verbose = verbose
    
    def run_tests(self) -> tuple[bool, list[tuple[str, bool]]]:
        """Run cargo tests and return (success, test_results)."""
        test_names = self._enumerate_tests()
        
        if not test_names:
            return self._fallback_test_run()
        
        return self._run_individual_tests(test_names)
    
    def _run_command(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Run subprocess command with consistent settings."""
        return subprocess.run(
            cmd,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    def _enumerate_tests(self) -> list[str]:
        """Extract test names from cargo test --list output."""
        result = self._run_command(["cargo", "test", "--", "--list"])
        output = result.stdout or ""
        
        test_names = []
        seen = set()
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # match patterns like "test name ... ok" or "name: test"
            patterns = [
                r'^(?:test\s+)?(?P<name>[\w:]+)\s*(?:\.\.\.|:)\s*(?:ok|FAILED|ignored)?$',
                r'^(?P<name>[\w:]+)\s*:\s*test$'
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    name = match.group("name")
                    if name and not name.startswith("running") and name not in seen:
                        seen.add(name)
                        test_names.append(name)
                    break
        
        return test_names
    
    def _fallback_test_run(self) -> tuple[bool, list[tuple[str, bool]]]:
        """Fallback to single cargo test run when enumeration fails."""
        if self.verbose:
            console.print("[yellow]warning: no tests enumerated. running single cargo test.[/yellow]")
        
        result = self._run_command(["cargo", "test", "-q"])
        success = result.returncode == 0
        
        if not success and self.verbose:
            console.print(result.stdout)
        
        return success, []
    
    def _run_individual_tests(self, test_names: list[str]) -> tuple[bool, list[tuple[str, bool]]]:
        """Run each test individually and collect results."""
        tests = []
        all_passed = True
        
        for i, name in enumerate(test_names, start=1):
            if self.verbose:
                console.print(f"running test {i}/{len(test_names)}: {name}")
            
            cmd = ["cargo", "test", name, "--", "--exact", "--nocapture"]
            result = self._run_command(cmd)
            passed = result.returncode == 0
            
            tests.append((name, passed))
            
            if not passed:
                all_passed = False
                if self.verbose:
                    console.print(result.stdout)
            elif self.verbose:
                console.print("  -> passed")
        
        return all_passed, tests


class ProgressTracker:
    """Manages exercise progress tracking."""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.progress = self._load_progress()
    
    def _load_progress(self) -> dict[str, bool]:
        """Load progress from JSON file."""
        if not self.progress_file.exists():
            return {}
        
        try:
            return json.loads(self.progress_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[yellow]warning: could not load progress file: {e}[/yellow]")
            return {}
    
    def save_progress(self, results: dict[str, bool]) -> None:
        """Save progress to JSON file."""
        self.progress.update(results)
        
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            self.progress_file.write_text(
                json.dumps(self.progress, indent=2),
                encoding="utf-8"
            )
        except OSError as e:
            console.print(f"[yellow]warning: could not save progress: {e}[/yellow]")
    
    def is_completed(self, project_name: str) -> bool:
        """Check if project is marked as completed."""
        return self.progress.get(project_name, False)


def find_scraper(url: str) -> tuple[str, Callable] | None:
    """Find appropriate scraper for given URL."""
    try:
        netloc = urlparse(url).netloc
    except Exception:
        return None
    
    for host, scraper_func in SCRAPERS.items():
        if host in netloc:
            source = host.split(".")[0]
            return source, scraper_func
    
    return None


def find_projects() -> list[Path]:
    """Find all Rust projects in exercises directory."""
    if not EXERCISES_DIR.exists():
        console.print(f"[red]error: exercises directory '{EXERCISES_DIR}' not found[/red]")
        raise click.Abort()
    
    projects = list(EXERCISES_DIR.rglob("Cargo.toml"))
    if not projects:
        console.print("[yellow]no rust projects found in exercises directory[/yellow]")
    
    return projects


def check_project(project_path: Path, verbose: bool) -> tuple[str, bool, list[tuple[str, bool]]]:
    """Check a single project and return results."""
    project_name = project_path.parent.name
    console.print(f"testing `{project_name}`...")
    
    runner = TestRunner(project_path.parent, verbose)
    success, tests = runner.run_tests()
    
    if not tests:
        console.print("- no individual tests detected")
    else:
        for idx, (name, passed) in enumerate(tests, start=1):
            status_color = "green" if passed else "red"
            status = f"passed" if passed else "failed"
            console.print(f"- [cyan]test {idx}[/cyan]:[{status_color}] {status} ({name}) [{status_color}]")
    
    console.print()
    
    return project_name, success, tests


def print_summary(results: dict[str, bool]) -> None:
    """Print summary of all test results."""
    console.print("[bold][u]summary:[/u][/bold]")
    for name, success in results.items():
        status_text = "(done)" if success else "(pending)"
        color = "green" if success else "yellow"
        console.print(f"- `{name}` [{color}]{status_text}[/{color}]")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli():
    """Scrape coding sites and generate Rust problem templates."""


@cli.command("url")
@click.argument("url")
def url_command(url: str):
    """Create Rust project from problem URL."""
    scraper_info = find_scraper(url)
    if not scraper_info:
        netloc = urlparse(url).netloc
        console.print(f"[red]error: unsupported site '{netloc}'[/red]")
        raise click.Abort()
    
    source, scraper_func = scraper_info
    
    try:
        data = scraper_func(url)
        data["source"] = source
        
        lib_content = render_rust_template(data, source)
        project_name = to_snake_case(data["title"])
        
        write_rust_project(project_name, lib_content)
        console.print(f"[green]successfully created project: {project_name}[/green]")
        
    except Exception as e:
        console.print(f"[red]error creating project: {e}[/red]")
        raise click.Abort()


@cli.command("check")
@click.option("--recheck", is_flag=True, help="Re-run all exercises regardless of saved state")
@click.option("--verbose", is_flag=True, help="Show detailed build/test output")
def check_command(recheck: bool, verbose: bool):
    """Check the status of all exercises in the exercises directory."""
    projects = find_projects()
    if not projects:
        return
    
    tracker = ProgressTracker(PROGRESS_FILE)
    results = {}
    
    for project_path in projects:
        project_name = project_path.parent.name
        
        # skip if already completed and not rechecking
        if not recheck and tracker.is_completed(project_name):
            results[project_name] = True
            continue
        
        project_name, success, _ = check_project(project_path, verbose)
        results[project_name] = success
    
    tracker.save_progress(results)
    print_summary(results)
    
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    cli()