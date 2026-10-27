"""Loads the named SQL blocks from sql/solution.sql.

The .sql file is the single source of truth: each block starts with a line
`-- name: <block_name>` and runs until the next `-- name:` line. The API never
builds SQL itself; it only binds parameters (:phone, :today) to these blocks.
"""

import re
from functools import lru_cache
from pathlib import Path

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "solution.sql"

_NAME_LINE = re.compile(r"^--\s*name:\s*(\w+)\s*$", re.MULTILINE)


@lru_cache(maxsize=1)
def load_queries(path: Path = SQL_FILE) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    matches = list(_NAME_LINE.finditer(text))
    blocks: dict[str, str] = {}
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[match.end():end]
        # Drop comment-only lines so the block is plain SQL.
        sql = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith("--")
        ).strip()
        blocks[match.group(1)] = sql
    return blocks


def query(name: str) -> str:
    return load_queries()[name]
