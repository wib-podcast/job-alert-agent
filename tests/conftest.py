"""
Test fixtures.

The storage tests need a real Postgres — psycopg's JSONB handling, ON CONFLICT
and `= ANY(%s)` are exactly the things a fake would get wrong, and they're the
parts worth testing.

Isolation is by schema rather than by database, so the suite is safe to point at
any Postgres it can reach — including the shared Neon instance — without ever
seeing or touching the real `jobs` table. Each run creates a uniquely named
schema, puts it first on the search_path, and drops it afterwards.
"""
from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()


def _base_dsn() -> "str | None":
    """
    Pick a database the schema trick actually works against.

    Order matters. Neon's *pooled* endpoint runs pgbouncer, which rejects
    `options=-csearch_path` at startup ("unsupported startup parameter"), so the
    pooled DATABASE_URL is the last resort rather than the first choice:

      TEST_DATABASE_URL     — CI's own Postgres service container, and the fast path.
      DATABASE_URL_UNPOOLED — Neon's direct endpoint, which accepts startup options.
      DATABASE_URL          — pooled; present so the failure is a clear error
                              rather than a confusing skip.
    """
    return (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL_UNPOOLED")
        or os.getenv("DATABASE_URL")
    )


@pytest.fixture(scope="session")
def base_dsn() -> str:
    dsn = _base_dsn()
    if not dsn:
        # In CI a missing database is a broken workflow, not a reason to pass.
        if os.getenv("CI"):
            raise RuntimeError(
                "TEST_DATABASE_URL is unset in CI. The storage tests would be "
                "skipped silently, which is worse than failing."
            )
        pytest.skip("No TEST_DATABASE_URL or DATABASE_URL set", allow_module_level=True)
    return dsn


@pytest.fixture
def dsn(base_dsn: str):
    """A DSN scoped to a throwaway schema, dropped when the test finishes."""
    schema = f"test_{uuid.uuid4().hex[:12]}"

    with psycopg.connect(base_dsn, autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')

    sep = "&" if "?" in base_dsn else "?"
    scoped = f"{base_dsn}{sep}options=-csearch_path%3D{schema}"

    try:
        from db import init_db

        init_db(scoped)
        yield scoped
    finally:
        with psycopg.connect(base_dsn, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
