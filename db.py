"""
Postgres storage layer.

All persistence goes through this module. No ORM — plain psycopg 3.

**The schema is owned by `web/src/lib/db/schema.ts`** and created by
`npm run db:push`. The DDL below mirrors it so that tests and a fresh local
checkout have a table to work against; in production the `IF NOT EXISTS` makes
it a no-op. If you add a column, change both files in the same commit —
`test_schema_contract.py` fails if the two drift on column names.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable, List

import psycopg
from psycopg.rows import dict_row

from models import JobCard

logger = logging.getLogger(__name__)

# The column contract, in table order. Shared by the DDL, the insert and the
# schema test so the three cannot disagree.
JOB_COLUMNS: tuple[str, ...] = (
    "id",
    "title",
    "company",
    "location",
    "geo",
    "job_url",
    "description",
    "source",
    "posted_date",
    "scraped_at",
    "relevance_score",
    "role_type",
    "org_stage",
    "recommended_cv",
    "cv_tweaks",
    "referee",
    "must_have_skills",
    "resume_gaps",
    "alerted",
    "status",
    "status_at",
)

_CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    company           TEXT NOT NULL,
    location          TEXT NOT NULL DEFAULT '',
    geo               TEXT NOT NULL DEFAULT 'IN',
    job_url           TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    source            TEXT NOT NULL,
    posted_date       TIMESTAMPTZ,
    scraped_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    relevance_score   DOUBLE PRECISION NOT NULL DEFAULT 0,
    role_type         TEXT,
    org_stage         TEXT,
    recommended_cv    TEXT,
    cv_tweaks         JSONB NOT NULL DEFAULT '[]'::jsonb,
    referee           JSONB,
    must_have_skills  JSONB NOT NULL DEFAULT '[]'::jsonb,
    resume_gaps       JSONB NOT NULL DEFAULT '[]'::jsonb,
    alerted           BOOLEAN NOT NULL DEFAULT false,
    status            TEXT NOT NULL DEFAULT 'new',
    status_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS jobs_score_idx  ON jobs (relevance_score, scraped_at);
CREATE INDEX IF NOT EXISTS jobs_geo_idx    ON jobs (geo);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs (status);
"""


def connect(dsn: str) -> psycopg.Connection:
    """Open a connection. Callers use it as a context manager."""
    return psycopg.connect(dsn, row_factory=dict_row)


def init_db(dsn: str) -> None:
    """Create the table and indexes if they don't exist."""
    with connect(dsn) as conn:
        conn.execute(_CREATE_JOBS_TABLE)
    logger.info("DB ready")


def job_exists(dsn: str, job_id: str) -> bool:
    with connect(dsn) as conn:
        row = conn.execute("SELECT 1 FROM jobs WHERE id = %s", (job_id,)).fetchone()
    return row is not None


def get_known_ids(dsn: str) -> set:
    """Every job ID already stored — lets scrapers skip detail-page fetches."""
    with connect(dsn) as conn:
        rows = conn.execute("SELECT id FROM jobs").fetchall()
    return {r["id"] for r in rows}


def save_job(dsn: str, job: JobCard) -> bool:
    """
    Insert a job. Returns True if inserted, False if it was already known.

    `ON CONFLICT DO NOTHING` rather than a read-then-write: two scrapers can
    find the same job in one run, and the check-then-insert version would let
    both through. The row count tells us which of the two we were.
    """
    with connect(dsn) as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs (
                id, title, company, location, geo, job_url, description, source,
                posted_date, scraped_at, relevance_score, role_type, org_stage,
                recommended_cv, cv_tweaks, referee, must_have_skills, resume_gaps,
                alerted
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            (
                job.id,
                job.title,
                job.company,
                job.location,
                job.geo,
                job.job_url,
                job.description,
                job.source,
                job.posted_date,
                job.scraped_at,
                job.relevance_score,
                job.role_type,
                job.org_stage,
                job.recommended_cv,
                json.dumps(job.cv_tweaks),
                json.dumps(job.referee) if job.referee else None,
                json.dumps(job.must_have_skills),
                json.dumps(job.resume_gaps),
                job.alerted,
            ),
        )
        return cur.rowcount == 1


def update_job(dsn: str, job: JobCard) -> None:
    """
    Write back the fields the scorer fills in.

    Deliberately does **not** touch `status` — that belongs to the person using
    the board, and a re-score must not resurrect something already dismissed.
    """
    with connect(dsn) as conn:
        conn.execute(
            """
            UPDATE jobs SET
                relevance_score  = %s,
                role_type        = %s,
                org_stage        = %s,
                recommended_cv   = %s,
                cv_tweaks        = %s,
                referee          = %s,
                must_have_skills = %s,
                resume_gaps      = %s,
                alerted          = %s
            WHERE id = %s
            """,
            (
                job.relevance_score,
                job.role_type,
                job.org_stage,
                job.recommended_cv,
                json.dumps(job.cv_tweaks),
                json.dumps(job.referee) if job.referee else None,
                json.dumps(job.must_have_skills),
                json.dumps(job.resume_gaps),
                job.alerted,
                job.id,
            ),
        )


def get_unalerted(dsn: str, min_score: float = 0.0) -> List[JobCard]:
    """
    Jobs that haven't been emailed yet, above a relevance threshold.

    Rejected jobs are excluded: if it's been rejected on the board, emailing it
    would be the agent arguing with its owner.
    """
    with connect(dsn) as conn:
        rows = conn.execute(
            """
            SELECT * FROM jobs
            WHERE alerted = false
              AND status <> 'dismissed'
              AND relevance_score >= %s
            ORDER BY relevance_score DESC
            """,
            (min_score,),
        ).fetchall()
    return [_row_to_job(r) for r in rows]


def mark_alerted(dsn: str, job_ids: Iterable[str]) -> None:
    ids = list(job_ids)
    if not ids:
        return
    with connect(dsn) as conn:
        conn.execute("UPDATE jobs SET alerted = true WHERE id = ANY(%s)", (ids,))


def _row_to_job(row: dict) -> JobCard:
    d = dict(row)
    # psycopg returns jsonb already decoded; a NULL stays None.
    d["cv_tweaks"] = d.get("cv_tweaks") or []
    d["must_have_skills"] = d.get("must_have_skills") or []
    d["resume_gaps"] = d.get("resume_gaps") or []
    d.pop("status", None)
    d.pop("status_at", None)
    return JobCard(**d)

