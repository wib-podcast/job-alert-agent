"""Tests for the JobCard contract every layer of the pipeline speaks."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import JobCard


def minimal(**overrides) -> dict:
    fields = {
        "id": "abc123",
        "title": "Product Manager",
        "company": "Acme",
        "location": "Remote",
        "job_url": "https://example.com/j/1",
        "source": "iimjobs",
    }
    fields.update(overrides)
    return fields


def test_a_freshly_scraped_card_starts_unscored_and_unalerted():
    job = JobCard(**minimal())
    assert job.relevance_score == 0.0
    assert job.alerted is False
    assert job.cv_tweaks == []
    assert job.resume_gaps == []
    assert job.referee is None


def test_relevance_score_is_bounded_to_the_scorer_s_scale():
    """The scorer is prompted for 0–10; a parse slip shouldn't reach the DB."""
    with pytest.raises(ValidationError):
        JobCard(**minimal(relevance_score=11.0))
    with pytest.raises(ValidationError):
        JobCard(**minimal(relevance_score=-1.0))


def test_unexpected_scraper_fields_are_ignored_not_fatal():
    """Scrapers evolve faster than the model; extra keys must not crash a run."""
    job = JobCard(**minimal(salary_range="₹40–60 LPA"))
    assert not hasattr(job, "salary_range")


def test_identity_fields_are_required():
    for missing in ("id", "title", "company", "job_url", "source"):
        fields = minimal()
        del fields[missing]
        with pytest.raises(ValidationError):
            JobCard(**fields)
