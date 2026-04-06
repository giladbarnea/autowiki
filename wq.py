#!/usr/bin/env python3
"""
wq.py — Query markdown YAML frontmatter with SQL (in-memory SQLite)

pip install pyyaml tabulate

USAGE
  python wq.py "SELECT ..." [--dir=PATH] [--format=table|csv|json] [--schema]

TABLE
  All records are loaded into a single table called `wiki`.
  Every column is TEXT. Dates compare correctly as ISO strings.
  Missing values are NULL.

SUPPORTED SQL
  SELECT col1, col2 | *
  WHERE  =  !=  <>  >  >=  <  <=  LIKE  IS NULL  IS NOT NULL
  AND  OR  NOT  (...)
  ORDER BY col ASC|DESC
  LIMIT n
  GROUP BY col  +  COUNT(*)  MIN()  MAX()  SUM()
  String fns: LOWER()  UPPER()  LENGTH()  SUBSTR()

  Only SELECT statements are accepted.

MAGIC COLUMN: text
  `text` contains the document body (everything after the YAML frontmatter).
  It is a real column — filterable, searchable — but has special rendering
  behaviour when --format=table (the default):

    SELECT text FROM wiki ...
      → raw body of each matching document

    SELECT text, name, created FROM wiki ...
      → each document rendered as a markdown file, but frontmatter contains
        only the selected non-text fields

    SELECT * FROM wiki ...
      → each document rendered verbatim (original file content)

  With --format=csv or --format=json, `text` is just another column.

LIST FIELDS (e.g. `keywords`)
  Stored as a JSON array. Query with json_each():

    SELECT name FROM wiki
    WHERE EXISTS (
      SELECT 1 FROM json_each(keywords) WHERE value = 'python'
    )

EXAMPLES
  python wq.py "SELECT name, created, summary FROM wiki ORDER BY created DESC LIMIT 20"
  python wq.py "SELECT name, created FROM wiki WHERE created > '2023-01-01'"
  python wq.py "SELECT name FROM wiki WHERE name LIKE '%auth%'"
  python wq.py "SELECT text FROM wiki WHERE name LIKE '%auth%'"
  python wq.py "SELECT text, name, created FROM wiki WHERE created > '2023-01-01'"
  python wq.py "SELECT * FROM wiki WHERE subject = 'engineering'"
  python wq.py "SELECT name FROM wiki WHERE EXISTS (SELECT 1 FROM json_each(keywords) WHERE value = 'python')"
  python wq.py "SELECT name FROM wiki WHERE text LIKE '%TODO%'"
  python wq.py "SELECT subject, COUNT(*) as n FROM wiki GROUP BY subject ORDER BY n DESC"
  python wq.py --schema
"""

import sys
import re
import json
import csv
import io
import sqlite3
import argparse
import textwrap
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ─── Frontmatter + body loader ───────────────────────────────────────────────

def load_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        return None

    try:
        data = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None

    # Body: everything after closing ---
    body_start = end + 4  # len("\n---") == 4
    if body_start < len(text) and text[body_start] == "\n":
        body_start += 1
    data["text"] = text[body_start:]

    data["_path"] = str(path)
    return data


def collect_records(root: Path) -> list[dict]:
    records = []
    for md in sorted(root.rglob("*.md")):
        fm = load_frontmatter(md)
        if fm:
            records.append(fm)
    return records


# ─── Schema inference ─────────────────────────────────────────────────────────

def infer_schema(records: list[dict]) -> tuple[list[str], set[str]]:
    """
    Returns:
      columns   — ordered list of all field names (text and _path last)
      list_cols — set of fields whose values are lists in at least one record
    """
    seen: dict[str, bool] = {}
    list_cols: set[str] = set()

    for r in records:
        for k, v in r.items():
            if k in ("text", "_path"):
                continue
            seen.setdefault(k, True)
            if isinstance(v, list):
                list_cols.add(k)

    cols = list(seen.keys())
    cols.append("text")
    cols.append("_path")
    return cols, list_cols


def serialize(value: Any, is_list_col: bool) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, default=str)
    if is_list_col:
        return json.dumps([value], ensure_ascii=False, default=str)
    return str(value)


# ─── DB builder ───────────────────────────────────────────────────────────────

def build_db(records: list[dict]) -> tuple[sqlite3.Connection, list[str], set[str]]:
    columns, list_cols = infer_schema(records)

    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(f"CREATE TABLE wiki ({col_defs})")

    placeholders = ", ".join("?" for _ in columns)
    for r in records:
        row = tuple(serialize(r.get(c), c in list_cols) for c in columns)
        con.execute(f"INSERT INTO wiki VALUES ({placeholders})", row)

    con.commit()
    return con, columns, list_cols


# ─── Query guard ──────────────────────────────────────────────────────────────

_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)

def guard(sql: str) -> None:
    if not _SELECT_RE.match(sql):
        sys.exit("Error: only SELECT statements are accepted.")


# ─── Document renderer (magic text column) ───────────────────────────────────

DIVIDER = "─" * 72

def _reconstruct_frontmatter(row: sqlite3.Row, meta_headers: list[str], list_cols: set[str]) -> str:
    """Build a YAML frontmatter block from selected non-text fields."""
    lines = ["---"]
    for h in meta_headers:
        v = row[h]
        if v is None:
            continue
        # Deserialize list cols back to a Python list for clean YAML output
        if h in list_cols and isinstance(v, str) and v.startswith("["):
            try:
                v = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                pass
        lines.append(yaml.dump({h: v}, default_flow_style=False, allow_unicode=True).rstrip())
    lines.append("---")
    return "\n".join(lines)


def render_documents(
    rows: list[sqlite3.Row],
    headers: list[str],
    all_columns: list[str],
    list_cols: set[str],
) -> str:
    if not rows:
        return "(no results)"

    meta_headers = [h for h in headers if h not in ("text", "_path")]
    only_text    = headers == ["text"]
    is_select_all = set(headers) == set(all_columns)

    blocks = []
    for row in rows:
        path = row["_path"] if "text" in headers or "_path" in headers else None
        header_line = f"── {path} " + DIVIDER[:max(0, 72 - len(str(path)) - 4)] if path else DIVIDER

        if only_text:
            body = row["text"] or ""
            blocks.append(f"{header_line}\n{body.rstrip()}")

        elif is_select_all:
            # Reconstruct full original file from all stored columns
            full_meta = [h for h in all_columns if h not in ("text", "_path")]
            fm = _reconstruct_frontmatter(row, full_meta, list_cols)
            body = row["text"] or ""
            blocks.append(f"{header_line}\n{fm}\n\n{body.rstrip()}")

        else:
            # Mixed: frontmatter with only selected meta fields
            fm = _reconstruct_frontmatter(row, meta_headers, list_cols) if meta_headers else ""
            body = row["text"] or ""
            if fm:
                blocks.append(f"{header_line}\n{fm}\n\n{body.rstrip()}")
            else:
                blocks.append(f"{header_line}\n{body.rstrip()}")

    return ("\n\n" + DIVIDER + "\n\n").join(blocks)


# ─── Table/CSV/JSON renderers ─────────────────────────────────────────────────

def fmt_cell(v: Any, max_width: int = 72) -> str:
    if v is None:
        return ""
    s = str(v)
    if s.startswith("["):
        try:
            items = json.loads(s)
            s = ", ".join(str(i) for i in items)
        except (json.JSONDecodeError, TypeError):
            pass
    return s if len(s) <= max_width else s[:max_width - 1] + "…"


def render_table(rows: list[sqlite3.Row], headers: list[str]) -> str:
    if not rows:
        return "(no results)"

    data = [[fmt_cell(row[h]) for h in headers] for row in rows]

    if HAS_TABULATE:
        return tabulate(data, headers=headers, tablefmt="rounded_outline")

    col_widths = [
        max(len(h), *(len(r[i]) for r in data))
        for i, h in enumerate(headers)
    ]
    sep = "┼".join("─" * (w + 2) for w in col_widths)
    header_row = "│".join(f" {h.ljust(col_widths[i])} " for i, h in enumerate(headers))
    lines = [header_row, sep]
    for row in data:
        lines.append("│".join(f" {cell.ljust(col_widths[i])} " for i, cell in enumerate(row)))
    return "\n".join(lines)


def render_csv(rows: list[sqlite3.Row], headers: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for row in rows:
        w.writerow([fmt_cell(row[h], max_width=10_000) for h in headers])
    return buf.getvalue()


def render_json(rows: list[sqlite3.Row], headers: list[str]) -> str:
    out = []
    for row in rows:
        record = {}
        for h in headers:
            v = row[h]
            if v is not None and isinstance(v, str) and v.startswith("["):
                try:
                    v = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    pass
            record[h] = v
        out.append(record)
    return json.dumps(out, ensure_ascii=False, indent=2)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        prog="wq.py",
        description="Query markdown YAML frontmatter with SQL (in-memory SQLite)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            EXAMPLES
              wq.py "SELECT name, created, summary FROM wiki ORDER BY created DESC LIMIT 20"
              wq.py "SELECT name, created FROM wiki WHERE created > '2023-01-01'"
              wq.py "SELECT name FROM wiki WHERE name LIKE '%auth%'"
              wq.py "SELECT text FROM wiki WHERE name = 'my-note'"
              wq.py "SELECT text, name, created FROM wiki WHERE subject = 'engineering'"
              wq.py "SELECT * FROM wiki WHERE subject = 'engineering'"
              wq.py "SELECT name FROM wiki WHERE text LIKE '%TODO%'"
              wq.py "SELECT name FROM wiki WHERE EXISTS (SELECT 1 FROM json_each(keywords) WHERE value = 'python')"
              wq.py "SELECT subject, COUNT(*) as n FROM wiki GROUP BY subject ORDER BY n DESC"
              wq.py --schema
        """),
    )
    p.add_argument("query", nargs="?", help="SQL SELECT statement (table is 'wiki')")
    p.add_argument("--dir",    metavar="PATH", default=".", help="Root directory to scan (default: .)")
    p.add_argument("--format", choices=["table", "csv", "json"], default="table")
    p.add_argument("--schema", action="store_true", help="Print column names and exit")

    args = p.parse_args()
    root = Path(args.dir).expanduser().resolve()

    if not root.is_dir():
        sys.exit(f"Error: '{root}' is not a directory")

    records = collect_records(root)
    if not records:
        sys.exit(f"No markdown files with frontmatter found under '{root}'")

    con, columns, list_cols = build_db(records)

    if args.schema:
        print(f"Table: wiki  ({len(records)} rows)\n")
        for c in columns:
            if c == "text":
                print(f"  {c}  [magic: document body]")
            elif c in list_cols:
                print(f"  {c}  [json list]")
            else:
                print(f"  {c}")
        print("\nList field query pattern:")
        print("  EXISTS (SELECT 1 FROM json_each(<col>) WHERE value = 'x')")
        print("\ntext column notes:")
        print("  SELECT text              → raw body output")
        print("  SELECT text, name, ...   → markdown with partial frontmatter")
        print("  SELECT *                 → full original document")
        return

    if not args.query:
        p.print_help()
        return

    guard(args.query)

    try:
        cur = con.execute(args.query)
    except sqlite3.Error as e:
        sys.exit(f"SQL error: {e}")

    rows = cur.fetchall()
    headers = [d[0] for d in cur.description] if cur.description else []

    use_doc_render = "text" in headers and args.format == "table"

    if use_doc_render:
        print(render_documents(rows, headers, columns, list_cols))
        print(f"\n{len(rows)} document(s)")
    elif args.format == "table":
        print(render_table(rows, headers))
        print(f"\n{len(rows)} row(s)")
    elif args.format == "csv":
        print(render_csv(rows, headers), end="")
    elif args.format == "json":
        print(render_json(rows, headers))


if __name__ == "__main__":
    main()
