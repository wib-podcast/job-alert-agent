"""
Tests for the storage layer, against a real Postgres in a throwaway schema.
See conftest.py for how the isolation works.
"""
from __future__ import annotations

from datetime import datetime, timezone

from db import (
    get_known_ids,
    get_unalerted,
    init_db,
    job_exists,
    mark_alerted,
    save_job,
    update_job,
)
from models import JobCard


def make_job(job_id: str = "abc123", **overrides) -> JobCard:
    fields = {
        "id": job_id,
        "title": "Senior Product Manager",
        "company": "Acme",
        "location": "Dubai",
        "geo": "AE",
        "job_url": f"https://example.com/j/{job_id}",
        "source": "bayt",
    }
    fields.update(overrides)
    return JobCard(**fields)


def test_save_job_returns_true_once_and_false_after(dsn):
    """Dedupe is why we only pay to score jobs we've never seen."""
    job = make_job()
    assert save_job(dsn, job) is True
    assert save_job(dsn, job) is False


def test_a_second_save_does_not_clobber_an_existing_score(dsn):
    """A re-scrape must not reset a score the LLM already paid to compute."""
    save_job(dsn, make_job())

    scored = make_job()
    scored.relevance_score = 8.5
    update_job(dsn, scored)

    save_job(dsn, make_job())  # seen again on the next run

    [stored] = get_unalerted(dsn)
    assert stored.relevance_score == 8.5


def test_round_trip_preserves_json_columns_and_types(dsn):
    job = make_job(
        posted_date=datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc),
        cv_tweaks=["Lead with the marketplace metric"],
        must_have_skills=["SQL", "Experimentation"],
        resume_gaps=["SQL"],
        referee={"name": "Someone", "role": "PM", "linkedin_url": "https://x"},
    )
    save_job(dsn, job)
    [stored] = get_unalerted(dsn)

    assert stored.cv_tweaks == ["Lead with the marketplace metric"]
    assert stored.must_have_skills == ["SQL", "Experimentation"]
    assert stored.resume_gaps == ["SQL"]
    assert stored.referee["name"] == "Someone"
    assert stored.posted_date == datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)
    assert stored.alerted is False


def test_geo_is_stored_and_folded_to_uppercase(dsn):
    save_job(dsn, make_job(geo="sg"))
    [stored] = get_unalerted(dsn)
    assert stored.geo == "SG"


def test_geo_defaults_to_india_when_a_scraper_omits_it(dsn):
    job = JobCard(
        id="no-geo",
        title="PM",
        company="Acme",
        location="Bangalore",
        job_url="https://example.com/j/1",
        source="iimjobs",
    )
    save_job(dsn, job)
    [stored] = get_unalerted(dsn)
    assert stored.geo == "IN"


def test_referee_and_optional_date_survive_as_none(dsn):
    save_job(dsn, make_job(referee=None, posted_date=None))
    [stored] = get_unalerted(dsn)
    assert stored.referee is None
    assert stored.posted_date is None


def test_get_unalerted_filters_by_threshold_and_sorts_desc(dsn):
    for job_id, score in [("low", 4.0), ("high", 9.0), ("mid", 7.5)]:
        job = make_job(job_id)
        save_job(dsn, job)
        job.relevance_score = score
        update_job(dsn, job)

    assert [j.id for j in get_unalerted(dsn, min_score=7.0)] == ["high", "mid"]


def test_get_unalerted_never_returns_a_dismissed_job(dsn):
    """Emailing something already dismissed is the agent arguing with its owner."""
    job = make_job()
    save_job(dsn, job)
    job.relevance_score = 9.0
    update_job(dsn, job)

    import db as db_module

    with db_module.connect(dsn) as conn:
        conn.execute("UPDATE jobs SET status = 'dismissed' WHERE id = %s", (job.id,))

    assert get_unalerted(dsn, min_score=7.0) == []


def test_update_job_leaves_board_status_alone(dsn):
    """Scoring is the pipeline's business; status belongs to the person."""
    job = make_job()
    save_job(dsn, job)

    import db as db_module

    with db_module.connect(dsn) as conn:
        conn.execute("UPDATE jobs SET status = 'saved' WHERE id = %s", (job.id,))

    job.relevance_score = 9.5
    update_job(dsn, job)

    with db_module.connect(dsn) as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id = %s", (job.id,)).fetchone()
    assert row["status"] == "saved"


def test_mark_alerted_removes_jobs_from_the_unalerted_queue(dsn):
    job = make_job()
    save_job(dsn, job)
    job.relevance_score = 9.0
    update_job(dsn, job)

    assert len(get_unalerted(dsn, min_score=7.0)) == 1
    mark_alerted(dsn, [job.id])
    assert get_unalerted(dsn, min_score=7.0) == []


def test_mark_alerted_with_an_empty_list_is_a_no_op(dsn):
    """send_digest returns [] when nothing was sent; that must not blow up."""
    mark_alerted(dsn, [])


def test_job_exists_and_get_known_ids_agree(dsn):
    save_job(dsn, make_job("one"))
    save_job(dsn, make_job("two"))

    assert job_exists(dsn, "one")
    assert not job_exists(dsn, "three")
    assert get_known_ids(dsn) == {"one", "two"}


def test_init_db_is_idempotent(dsn):
    save_job(dsn, make_job())
    init_db(dsn)
    assert job_exists(dsn, "abc123")
