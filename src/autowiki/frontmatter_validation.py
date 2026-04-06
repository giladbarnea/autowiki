from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from autowiki.frontmatter import read_markdown


IGNORED_ROOT_MARKDOWN = {"AGENTS.md", "README.md"}


@dataclass(slots=True)
class ValidationIssue:
    path: Path
    message: str


def lint_staged_frontmatter(repo_root: Path) -> list[ValidationIssue]:
    staged_files = get_staged_markdown_files(repo_root)
    return validate_staged_markdown_files(
        repo_root=repo_root,
        new_paths=staged_files.new_paths,
        modified_paths=staged_files.modified_paths,
    )


@dataclass(slots=True)
class StagedMarkdownFiles:
    new_paths: list[Path]
    modified_paths: list[Path]


def get_staged_markdown_files(repo_root: Path) -> StagedMarkdownFiles:
    completed = subprocess.run(
        [
            "git",
            "--no-pager",
            "diff",
            "--cached",
            "--name-status",
            "--diff-filter=AM",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    new_paths: list[Path] = []
    modified_paths: list[Path] = []

    for line in completed.stdout.splitlines():
        if not line.strip():
            continue

        status, relative_path_text = line.split("\t", maxsplit=1)
        relative_path = Path(relative_path_text)
        absolute_path = repo_root / relative_path

        if not should_validate_markdown_path(relative_path):
            continue

        if status == "A":
            new_paths.append(absolute_path)
            continue

        if status == "M":
            modified_paths.append(absolute_path)

    return StagedMarkdownFiles(
        new_paths=new_paths,
        modified_paths=modified_paths,
    )


def should_validate_markdown_path(relative_path: Path) -> bool:
    if relative_path.suffix.lower() != ".md":
        return False

    if len(relative_path.parts) == 1 and relative_path.name in IGNORED_ROOT_MARKDOWN:
        return False

    return not any(part.startswith(".") for part in relative_path.parts)


def validate_staged_markdown_files(
    repo_root: Path,
    new_paths: list[Path],
    modified_paths: list[Path],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for path in new_paths:
        issues.extend(validate_new_markdown_file(repo_root=repo_root, path=path))

    for path in modified_paths:
        issues.extend(validate_modified_markdown_file(repo_root=repo_root, path=path))

    return issues


def validate_new_markdown_file(repo_root: Path, path: Path) -> list[ValidationIssue]:
    document = read_markdown(path)
    relative_path = path.relative_to(repo_root)

    if document.parse_error:
        return [ValidationIssue(path=path, message=f"{relative_path}: {document.parse_error}")]

    created_value = document.get("created")
    if created_value is None or not str(created_value).strip():
        return [
            ValidationIssue(
                path=path,
                message=(
                    f"{relative_path}: newly added markdown files must include a non-empty "
                    "`created` frontmatter field."
                ),
            )
        ]

    return []


def validate_modified_markdown_file(repo_root: Path, path: Path) -> list[ValidationIssue]:
    document = read_markdown(path)
    relative_path = path.relative_to(repo_root)

    if document.parse_error:
        return [ValidationIssue(path=path, message=f"{relative_path}: {document.parse_error}")]

    updated_value = document.get("updated")
    if updated_value is None or not str(updated_value).strip():
        return [
            ValidationIssue(
                path=path,
                message=(
                    f"{relative_path}: modified markdown files must include a non-empty "
                    "`updated` frontmatter field."
                ),
            )
        ]

    updated_date = parse_iso_date(updated_value)
    if updated_date is None:
        return [
            ValidationIssue(
                path=path,
                message=(
                    f"{relative_path}: `updated` must be an ISO date like YYYY-MM-DD. "
                    f"Got {updated_value!r}."
                ),
            )
        ]

    filesystem_modified_date = datetime.fromtimestamp(path.stat().st_mtime).date()
    if updated_date < filesystem_modified_date:
        return [
            ValidationIssue(
                path=path,
                message=(
                    f"{relative_path}: `updated` is {updated_date.isoformat()}, which is older "
                    f"than the file modification date {filesystem_modified_date.isoformat()}."
                ),
            )
        ]

    return []


def parse_iso_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    stripped_value = value.strip()
    if not stripped_value:
        return None

    try:
        return date.fromisoformat(stripped_value)
    except ValueError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autowiki lint-frontmatter",
        description="Validate frontmatter requirements for staged markdown files.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Validate staged markdown files in the current git repository.",
    )
    args = parser.parse_args(argv)

    if not args.staged:
        parser.error("Pass --staged to validate staged markdown files.")

    repo_root = discover_repo_root(Path.cwd())
    issues = lint_staged_frontmatter(repo_root)
    if not issues:
        return 0

    print("Frontmatter validation failed:", file=sys.stderr)
    for issue in issues:
        print(f"- {issue.message}", file=sys.stderr)
    return 1


def discover_repo_root(start_path: Path) -> Path:
    completed = subprocess.run(
        ["git", "--no-pager", "rev-parse", "--show-toplevel"],
        cwd=start_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(completed.stdout.strip())
