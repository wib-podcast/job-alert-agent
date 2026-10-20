"""
MyCareersFuture (Singapore) — the government job portal.

The only Tier 1 source that needs no key, no browser and no account: it is a
plain JSON API over HTTPS. Singapore law requires every Employment Pass and
S Pass–eligible role to be advertised here for 14 days, which makes it the most
complete record of foreign-hire-eligible roles in the market — exactly the
subset that matters to someone relocating. See SOURCES.md.

Two endpoints:
  POST /v2/search      — paged results, no description
  GET  /v2/jobs/{uuid} — the full posting, including description

The search response has everything except the description, so detail fetches are
the expensive part. `known_ids` skips them for jobs already stored.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from models import JobCard
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_API = "https://api.mycareersfuture.gov.sg/v2"
_PAGE_SIZE = 20
_TIMEOUT = 30

# Sent because the API is public but unadvertised; a generic agent string gets
# throttled less than python-requests' default.
_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _make_job_id(uuid: str) -> str:
    """Keyed on the portal's own UUID, which is stable across re-listings."""
    return hashlib.sha1(f"mycareersfuture:{uuid}".encode()).hexdigest()


def _job_url(result: Dict[str, Any]) -> str:
    """
    Prefer the portal's own canonical URL; fall back to one built from the UUID.

    The fallback matters: jobDetailsUrl is inside `metadata`, and a posting that
    arrives without it would otherwise have no link at all in the digest.
    """
    url = (result.get("metadata") or {}).get("jobDetailsUrl")
    if url:
        return str(url)
    return f"https://www.mycareersfuture.gov.sg/job/{result.get('uuid', '')}"


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n{3,}")


def strip_html(raw: Optional[str]) -> str:
    """
    Descriptions come back as HTML. The scorer reads plain text, and paying
    Claude to tokenise `<p>` tags is waste.

    Block-level tags become newlines so paragraph and list structure survives —
    a wall of run-together text scores worse than one that still reads as a job
    description.
    """
    if not raw:
        return ""
    text = re.sub(r"(?i)<(br|/p|/li|/h[1-6]|/div)[^>]*>", "\n", raw)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _WS_RE.sub("\n\n", text).strip()


def _salary_line(salary: Optional[Dict[str, Any]]) -> str:
    """
    A one-line salary summary prepended to the description.

    Worth the tokens: salary is one of the strongest relevance signals for a
    relocation decision, and it is structured here when most boards hide it.
    """
    if not salary:
        return ""
    lo, hi = salary.get("minimum"), salary.get("maximum")
    if not lo and not hi:
        return ""
    period = ((salary.get("type") or {}).get("salaryType") or "Monthly").lower()
    if lo and hi:
        return f"Salary: SGD {lo:,}–{hi:,} {period}"
    return f"Salary: SGD {(lo or hi):,} {period}"


def _posted_date(result: Dict[str, Any]) -> Optional[datetime]:
    raw = (result.get("metadata") or {}).get("newPostingDate")
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        logger.debug("MyCareersFuture: unparseable posting date %r", raw)
        return None


def to_job_card(result: Dict[str, Any], detail: Optional[Dict[str, Any]] = None) -> Optional[JobCard]:
    """
    Turn one search result (plus its optional detail payload) into a JobCard.

    Pure — no network — so it is the part the tests exercise against a recorded
    fixture. Returns None for a result with no title or no UUID, because a job
    we can't identify can't be deduplicated.
    """
    uuid = result.get("uuid")
    title = (result.get("title") or "").strip()
    if not uuid or not title:
        return None

    company = ((result.get("postedCompany") or {}).get("name") or "").strip()
    if not company:
        # isHideHiringEmployerName postings are real jobs through an agency.
        company = "Undisclosed"

    parts = [_salary_line(result.get("salary"))]
    if detail:
        parts.append(strip_html(detail.get("description")))
        years = detail.get("minimumYearsExperience")
        if years:
            parts.insert(1, f"Minimum experience: {years} years")
    description = "\n\n".join(p for p in parts if p)[:4000]

    levels = [lvl.get("position") for lvl in (result.get("positionLevels") or []) if lvl.get("position")]

    return JobCard(
        id=_make_job_id(str(uuid)),
        title=title,
        company=company.title() if company.isupper() else company,
        location="Singapore",
        geo="SG",
        job_url=_job_url(result),
        description=description,
        source="mycareersfuture",
        posted_date=_posted_date(result),
        role_type=levels[0] if levels else None,
    )


def _search(session: requests.Session, term: str, page: int) -> List[Dict[str, Any]]:
    resp = session.post(
        f"{_API}/search",
        params={"limit": _PAGE_SIZE, "page": page, "sortBy": "new_posting_date"},
        json={"search": term},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("results") or []


def _detail(session: requests.Session, uuid: str) -> Optional[Dict[str, Any]]:
    try:
        resp = session.get(f"{_API}/jobs/{uuid}", timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        # One missing description shouldn't lose the whole page of results.
        logger.debug("MyCareersFuture: detail fetch failed for %s: %s", uuid, exc)
        return None


def _scrape_sync(
    roles: List[str], max_jobs_per_query: int, days_since_posted: int, known_ids: set
) -> List[JobCard]:
    cutoff = datetime.now(tz=timezone.utc).timestamp() - days_since_posted * 86_400
    jobs: List[JobCard] = []
    seen: set = set()

    with requests.Session() as session:
        session.headers.update(_HEADERS)

        for role in roles:
            fetched = 0
            for page in range((max_jobs_per_query // _PAGE_SIZE) + 1):
                if fetched >= max_jobs_per_query:
                    break
                try:
                    results = _search(session, role, page)
                except requests.RequestException as exc:
                    logger.warning("MyCareersFuture: search failed for %r: %s", role, exc)
                    break
                if not results:
                    break

                for result in results:
                    if fetched >= max_jobs_per_query:
                        break

                    uuid = result.get("uuid")
                    if not uuid:
                        continue

                    job_id = _make_job_id(str(uuid))
                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    posted = _posted_date(result)
                    if posted and posted.timestamp() < cutoff:
                        # Sorted newest first, so the rest of this page is older too.
                        break

                    # Anything already stored is skipped before the detail
                    # fetch — that request is the expensive part of this scraper.
                    if job_id in known_ids:
                        continue

                    card = to_job_card(result, _detail(session, str(uuid)))
                    if card:
                        jobs.append(card)
                        fetched += 1

            logger.info("MyCareersFuture: %d jobs for %r", fetched, role)

    return jobs


class MyCareersFutureScraper(BaseScraper):
    source = "mycareersfuture"

    def __init__(self, max_jobs_per_query: int = 30, days_since_posted: int = 14):
        self.max_jobs_per_query = max_jobs_per_query
        self.days_since_posted = days_since_posted

    async def scrape(
        self, roles: List[str], locations: List[str], dsn: Optional[str] = None
    ) -> List[JobCard]:
        """
        `locations` is ignored — this portal is Singapore by definition, and
        pretending otherwise would silently return Singapore jobs for a Dubai
        query. Geography selection happens by choosing the scraper.
        """
        from db import get_known_ids

        known_ids: set = get_known_ids(dsn) if dsn else set()

        jobs = await asyncio.to_thread(
            _scrape_sync, roles, self.max_jobs_per_query, self.days_since_posted, known_ids
        )
        logger.info("MyCareersFuture: total unique jobs = %d", len(jobs))
        return jobs
