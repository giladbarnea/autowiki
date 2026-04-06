from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from autowiki.frontmatter import collect_markdown_documents, read_markdown
from autowiki.frontmatter_validation import should_validate_markdown_path

INDEX_FILE_NAME = "index.md"


@dataclass(slots=True)
class PageRecord:
    path: Path
    title: str
    summary: str
    keywords: list[str]
    created: str | None
    updated: str | None

    @property
    def depth(self) -> int:
        return len(self.path.parts)

    @property
    def section_key(self) -> str:
        return self.path.parts[0] if self.depth > 1 else "(root)"


def generate_index(repo_root: Path) -> str:
    records = _collect_records(repo_root)

    existing_index = repo_root / INDEX_FILE_NAME
    existing_created = _existing_created_date(existing_index)
    today = date.today().isoformat()

    header = [
        "---",
        "title: index.md",
        "summary: Content-oriented breadth-first catalog of the wiki generated from YAML frontmatter.",
        "keywords:",
        "  - index",
        "  - catalog",
        "  - frontmatter",
        "  - navigation",
        f"created: {existing_created or today}",
        f"updated: {today}",
        "---",
        "",
        "# Index",
        "",
        "This file is auto-generated from YAML frontmatter and organized breadth-first for fast traversal.",
        "",
        "## Snapshot",
        "",
        f"- Pages indexed: {len(records)}",
    ]

    top_keywords = _top_keywords(records)
    if top_keywords:
        header.append(f"- Frequent keywords: {', '.join(top_keywords)}")

    body = ["", "## Catalog (breadth-first)", ""]

    if not records:
        body.extend(["_No indexable markdown pages found._", ""])
        return "\n".join(header + body)

    grouped: dict[str, list[PageRecord]] = defaultdict(list)
    for record in records:
        grouped[record.section_key].append(record)

    section_order = sorted(grouped.keys(), key=lambda name: (name != "(root)", name.lower()))

    for section in section_order:
        body.append(f"### {section}")
        body.append("")

        ordered_records = sorted(
            grouped[section],
            key=lambda record: (record.depth, str(record.path).lower()),
        )

        for record in ordered_records:
            indent = "  " * max(record.depth - 1, 0)
            rel = record.path.as_posix()
            summary = record.summary.strip().replace("\n", " ")
            body.append(f"{indent}- [{record.title}]({rel}) — {summary}")

            meta_parts: list[str] = []
            if record.created:
                meta_parts.append(f"created: {record.created}")
            if record.updated:
                meta_parts.append(f"updated: {record.updated}")
            if record.keywords:
                meta_parts.append(f"keywords: {', '.join(record.keywords)}")
            if meta_parts:
                body.append(f"{indent}  - {' | '.join(meta_parts)}")

        body.append("")

    return "\n".join(header + body)


def write_index(repo_root: Path) -> Path:
    target = repo_root / INDEX_FILE_NAME
    target.write_text(generate_index(repo_root), encoding="utf-8")
    return target


def _collect_records(repo_root: Path) -> list[PageRecord]:
    records: list[PageRecord] = []
    for document in collect_markdown_documents(repo_root):
        if not document.path:
            continue

        rel = document.path.relative_to(repo_root)
        if rel.name == INDEX_FILE_NAME:
            continue

        if not should_validate_markdown_path(rel):
            continue

        if document.parse_error or not document.has_frontmatter:
            continue

        title = str(document.get("title") or "").strip()
        summary = str(document.get("summary") or "").strip()
        raw_keywords = document.get("keywords")
        keywords = [str(keyword).strip() for keyword in raw_keywords] if isinstance(raw_keywords, list) else []

        if not title or not summary:
            continue

        created = _string_or_none(document.get("created"))
        updated = _string_or_none(document.get("updated"))

        records.append(
            PageRecord(
                path=rel,
                title=title,
                summary=summary,
                keywords=[keyword for keyword in keywords if keyword],
                created=created,
                updated=updated,
            )
        )

    return records


def _top_keywords(records: list[PageRecord], limit: int = 8) -> list[str]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record.keywords)

    return [keyword for keyword, _ in counts.most_common(limit)]


def _existing_created_date(index_path: Path) -> str | None:
    if not index_path.exists():
        return None

    existing_index = read_markdown(index_path)
    if existing_index.parse_error or not existing_index.has_frontmatter:
        return None

    created = existing_index.get("created")
    if not isinstance(created, str):
        return None

    stripped = created.strip()
    return stripped or None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None

    string_value = str(value).strip()
    return string_value or None
