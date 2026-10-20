"""
Job IDs are the dedupe key. If the derivation changes, every job in history
looks new again and the next digest re-alerts all of it — so these are pinned.
See AGENTS.md ("Deduplication is by stable ID, computed at scrape time").
"""
from __future__ import annotations

from scrapers.iimjobs import _make_job_id as iimjobs_id
from scrapers.linkedin import _make_job_id as linkedin_id


def test_the_same_url_always_yields_the_same_id():
    url = "https://www.iimjobs.com/j/senior-product-manager-1234567"
    assert iimjobs_id(url) == iimjobs_id(url)


def test_different_urls_yield_different_ids():
    assert iimjobs_id("https://www.iimjobs.com/j/a-1") != iimjobs_id(
        "https://www.iimjobs.com/j/a-2"
    )


def test_linkedin_ignores_tracking_params():
    """LinkedIn appends refId/trackingId, which would fake a new job each run."""
    bare = "https://www.linkedin.com/jobs/view/3912345678"
    tracked = "https://www.linkedin.com/jobs/view/3912345678/?refId=xyz&trackingId=abc"
    assert linkedin_id(bare) == linkedin_id(tracked)


def test_linkedin_ignores_a_slug_before_the_job_id():
    with_slug = "https://www.linkedin.com/jobs/view/3912345678/?currentJobId=3912345678"
    assert linkedin_id(with_slug) == linkedin_id(
        "https://www.linkedin.com/jobs/view/3912345678"
    )


def test_sources_do_not_collide_on_the_same_path():
    """The source prefix is what keeps two boards' IDs apart."""
    assert iimjobs_id("https://x/123") != linkedin_id("https://x/jobs/view/123")
