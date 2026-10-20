"""
The Python DDL and the Drizzle schema describe the same table.

Python writes the rows; the web board reads them. Nothing enforces that at
runtime, so a rename on one side shows up as a scrape that succeeds and stores
nothing. This test compares the two files directly.
"""
from __future__ import annotations

import pathlib
import re

from db import JOB_COLUMNS, _CREATE_JOBS_TABLE

SCHEMA_TS = pathlib.Path(__file__).parent.parent / "web" / "src" / "lib" / "db" / "schema.ts"


def _ddl_columns() -> "set[str]":
    """Column names from the CREATE TABLE body only — not the index statements."""
    body = _CREATE_JOBS_TABLE.split("(", 1)[1].split("\n);", 1)[0]
    cols = set()
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        cols.add(line.split()[0].strip(","))
    return cols


def _drizzle_columns() -> "set[str]":
    """
    SQL column names from the `jobs` table definition only.

    Scoped to that one export because schema.ts also declares `settings`, whose
    columns would otherwise look like columns db.py had forgotten. Matches
    `name: type("sql_name")` declarations; index lines like
    `index("jobs_geo_idx").on(...)` have no `name:` prefix and so don't match.
    """
    text = SCHEMA_TS.read_text()
    start = text.index("export const jobs = pgTable(")
    rest = text[start:]
    # Stop at the next top-level export, so only the jobs block is scanned.
    nxt = rest.find("\nexport const ", 1)
    block = rest if nxt == -1 else rest[:nxt]
    return set(re.findall(r'^\s+\w+:\s*\w+\("([a-z_]+)"', block, re.MULTILINE))


def test_the_ddl_matches_the_declared_column_contract():
    assert _ddl_columns() == set(JOB_COLUMNS)


def test_python_and_drizzle_agree_on_every_column_name():
    missing_in_ts = set(JOB_COLUMNS) - _drizzle_columns()
    extra_in_ts = _drizzle_columns() - set(JOB_COLUMNS)
    assert not missing_in_ts, f"Drizzle schema is missing: {sorted(missing_in_ts)}"
    assert not extra_in_ts, f"db.py is missing: {sorted(extra_in_ts)}"
