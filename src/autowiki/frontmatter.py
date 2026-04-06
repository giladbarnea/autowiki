from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml


FRONTMATTER_DELIMITER = "---"


@dataclass(slots=True)
class MarkdownDocument:
    body: str
    frontmatter: dict[str, object] = field(default_factory=dict)
    has_frontmatter: bool = False
    parse_error: str | None = None
    path: Path | None = None

    def get(self, key: str, default: object | None = None) -> object | None:
        return self.frontmatter.get(key, default)

    def set(self, key: str, value: object) -> None:
        self.frontmatter[key] = value

    def update(self, values: Mapping[str, object]) -> None:
        self.frontmatter.update(values)

    def delete(self, key: str) -> None:
        self.frontmatter.pop(key, None)

    def render(self) -> str:
        if not self.frontmatter:
            return self.body

        rendered_frontmatter = yaml.safe_dump(
            self.frontmatter,
            allow_unicode=True,
            sort_keys=False,
        ).strip()
        rendered = f"{FRONTMATTER_DELIMITER}\n{rendered_frontmatter}\n{FRONTMATTER_DELIMITER}"
        if not self.body:
            return f"{rendered}\n"
        if self.body.startswith("\n"):
            return f"{rendered}{self.body}"
        return f"{rendered}\n{self.body}"

    def write(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            raise ValueError("No target path provided for MarkdownDocument.write().")

        target.write_text(self.render(), encoding="utf-8")


def parse_markdown(text: str, path: Path | None = None) -> MarkdownDocument:
    if not text:
        return MarkdownDocument(body="", path=path)

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return MarkdownDocument(body=text, path=path)

    closing_index = _find_closing_frontmatter_line(lines)
    if closing_index is None:
        return MarkdownDocument(
            body=text,
            parse_error="Frontmatter opening delimiter is missing a closing delimiter.",
            path=path,
        )

    raw_frontmatter = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :])
    body = _strip_single_leading_newline(body)

    try:
        loaded = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError as exc:
        return MarkdownDocument(
            body=body,
            parse_error=f"Invalid YAML frontmatter: {exc}",
            path=path,
        )

    if not isinstance(loaded, dict):
        return MarkdownDocument(
            body=body,
            parse_error="Frontmatter must parse to a YAML mapping.",
            path=path,
        )

    normalized_frontmatter = {str(key): value for key, value in loaded.items()}
    return MarkdownDocument(
        body=body,
        frontmatter=normalized_frontmatter,
        has_frontmatter=True,
        path=path,
    )


def read_markdown(path: Path) -> MarkdownDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_markdown(text, path=path)


def collect_markdown_documents(root: Path) -> list[MarkdownDocument]:
    documents: list[MarkdownDocument] = []
    for path in sorted(_iter_markdown_paths(root)):
        documents.append(read_markdown(path))
    return documents


def _iter_markdown_paths(root: Path) -> Iterable[Path]:
    return root.rglob("*.md")


def _find_closing_frontmatter_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIMITER:
            return index
    return None


def _strip_single_leading_newline(text: str) -> str:
    if text.startswith("\r\n"):
        return text[2:]
    if text.startswith("\n"):
        return text[1:]
    return text
