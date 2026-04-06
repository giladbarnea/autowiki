from __future__ import annotations

import argparse

from autowiki.frontmatter_validation import main as lint_frontmatter_main


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

    args = parser.parse_args()
    if args.command == "lint-frontmatter":
        raise SystemExit(lint_frontmatter_main(["--staged"] if args.staged else []))

    parser.print_help()
