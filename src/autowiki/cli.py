from __future__ import annotations

import argparse
from pathlib import Path

from autowiki.frontmatter_validation import main as lint_frontmatter_main
from autowiki.index_builder import write_index


def main() -> None:
    parser = argparse.ArgumentParser(prog="autowiki")
    subparsers = parser.add_subparsers(dest="command")

    lint_frontmatter_parser = subparsers.add_parser(
        "lint-frontmatter",
        help="Validate frontmatter requirements for staged markdown files.",
    )
    lint_frontmatter_parser.add_argument(
        "--staged",
        action="store_true",
        help="Validate staged markdown files in the current git repository.",
    )

    generate_index_parser = subparsers.add_parser(
        "generate-index",
        help="Generate index.md from markdown frontmatter.",
    )
    generate_index_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: current directory).",
    )

    args = parser.parse_args()
    if args.command == "lint-frontmatter":
        raise SystemExit(lint_frontmatter_main(["--staged"] if args.staged else []))

    if args.command == "generate-index":
        write_index(Path(args.repo_root).resolve())
        return

    parser.print_help()
