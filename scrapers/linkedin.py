"""
LinkedIn Jobs scraper — Playwright + session cookies.

Setup: Export cookies from linkedin.com using Cookie-Editor Chrome extension,
save as JSON to data/linkedin_cookies.json. See dashboard LinkedIn Setup tab.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Page, BrowserContext

from models import JobCard
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_BASE = "https://www.linkedin.com"
_COOKIES_PATH = Path(__file__).parent.parent / "data" / "linkedin_cookies.json"


def _make_job_id(url: str) -> str:
    # Normalise LinkedIn job URLs (strip query params, keep job ID)
    job_id_part = url.split("/jobs/view/")[-1].split("/")[0].split("?")[0]
    return hashlib.sha1(f"linkedin:{job_id_part}".encode()).hexdigest()


def _parse_relative_date(text: str) -> Optional[datetime]:
    """Convert '3 days ago', '1 week ago' etc. to datetime."""
    text = text.strip().lower()
    now = datetime.now(tz=timezone.utc)
    if "hour" in text:
        n = int(text.split()[0]) if text.split()[0].isdigit() else 1
        return now - timedelta(hours=n)
    if "day" in text:
        n = int(text.split()[0]) if text.split()[0].isdigit() else 1
        return now - timedelta(days=n)
    if "week" in text:
        n = int(text.split()[0]) if text.split()[0].isdigit() else 1
        return now - timedelta(weeks=n)
    if "month" in text:
        n = int(text.split()[0]) if text.split()[0].isdigit() else 1
        return now - timedelta(days=n * 30)
    return None


def _read_cookie_json() -> Optional[str]:
    """
    Cookies from the settings table first, then the local file.

    The database copy is what lets a scheduled run use LinkedIn at all — the
    local file only ever existed on the laptop. The file stays as a fallback so
    an offline local run still works.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        try:
            import psycopg

            with psycopg.connect(url, connect_timeout=10) as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = 'LINKEDIN_COOKIES'"
                ).fetchone()
            if row and row[0]:
                logger.info("LinkedIn: using cookies from the settings table")
                return row[0]
        except Exception as exc:  # noqa: BLE001 — fall back to the file
            logger.debug("LinkedIn: could not read cookies from DB: %s", exc)

    if _COOKIES_PATH.exists():
        logger.info("LinkedIn: using cookies from %s", _COOKIES_PATH)
        return _COOKIES_PATH.read_text()

    return None


async def _load_cookies(context: BrowserContext) -> bool:
    """Load saved LinkedIn session cookies into Playwright context."""
    raw_json = _read_cookie_json()
    if not raw_json:
        logger.error("LinkedIn cookies not found. See the board's LinkedIn Setup tab.")
        return False
    try:
        raw = json.loads(raw_json)
        # Normalise: Cookie-Editor uses "sameSite" with values like "no_restriction"
        _samesite_map = {"no_restriction": "None", "lax": "Lax", "strict": "Strict", "unspecified": "None"}
        cookies = []
        for c in raw:
            sam = c.get("sameSite", "None")
            if isinstance(sam, str):
                sam = _samesite_map.get(sam.lower(), "None")
            else:
                sam = "None"
            cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".linkedin.com"),
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", False),
                "sameSite": sam,
            })
        await context.add_cookies(cookies)
        logger.info(f"Loaded {len(cookies)} LinkedIn cookies")
        return True
    except Exception as exc:
        logger.error(f"Failed to load LinkedIn cookies: {exc}")
        return False


async def _get_job_links(page: Page, role: str, location: str, days: int = 14) -> List[str]:
    """Navigate to LinkedIn Jobs search and return job detail URLs."""
    # f_TPR filter: r86400=1day, r259200=3days, r604800=7days, r1209600=14days, r2592000=30days
    tpr_map = {1: "r86400", 3: "r259200", 7: "r604800", 14: "r1209600", 30: "r2592000"}
    tpr = tpr_map.get(days, "r1209600")
    url = (
        f"{_BASE}/jobs/search/?keywords={quote_plus(role)}"
        f"&location={quote_plus(location)}&f_TPR={tpr}&sortBy=DD"
    )
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2000)
    except Exception as exc:
        logger.warning(f"LinkedIn search page failed: {exc}")
        return []

    # Scroll to load more cards
    for _ in range(4):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(800)

    links = await page.evaluate("""() => {
        const seen = new Set();
        const results = [];
        document.querySelectorAll('a[href*="/jobs/view/"]').forEach(a => {
            const url = a.href.split('?')[0];
            if (!seen.has(url)) { seen.add(url); results.push(url); }
        });
        return results;
    }""")
    logger.info(f"LinkedIn: found {len(links)} job links for '{role}' / '{location}'")
    return links


async def _parse_job_detail(page: Page, url: str) -> Optional[JobCard]:
    """Visit a LinkedIn job detail page and extract fields."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(1500)
    except Exception as exc:
        logger.debug(f"LinkedIn detail page failed ({url}): {exc}")
        return None

    try:
        data = await page.evaluate("""() => {
            const get = sel => document.querySelector(sel)?.innerText?.trim() || '';
            return {
                title:       get('h1.top-card-layout__title, h1.t-24, h1'),
                company:     get('a.topcard__org-name-link, .top-card-layout__first-subline a, span.topcard__flavor'),
                location:    get('.topcard__flavor--bullet, .top-card-layout__first-subline .topcard__flavor:last-child'),
                posted_text: get('span.posted-time-ago__text, .top-card-layout__first-subline time'),
                description: get('.show-more-less-html__markup, .description__text, .job-description'),
            };
        }""")

        title = data.get("title", "").strip()
        if not title:
            return None

        company = data.get("company", "").strip() or "Unknown"
        location = data.get("location", "").strip()
        description = (data.get("description") or "")[:4000]
        posted_text = data.get("posted_text", "")
        posted_date = _parse_relative_date(posted_text) if posted_text else None

        return JobCard(
            id=_make_job_id(url),
            title=title,
            company=company,
            location=location,
            job_url=url,
            description=description,
            source="linkedin",
            posted_date=posted_date,
        )
    except Exception as exc:
        logger.debug(f"LinkedIn parse error ({url}): {exc}")
        return None


class LinkedInScraper(BaseScraper):
    source = "linkedin"

    def __init__(self, max_jobs_per_query: int = 25, days_since_posted: int = 14):
        self.max_jobs_per_query = max_jobs_per_query
        self.days_since_posted = days_since_posted

    async def scrape(self, roles: List[str], locations: List[str], dsn=None) -> List[JobCard]:
        from db import get_known_ids
        known_ids: set = get_known_ids(dsn) if dsn else set()
        jobs: List[JobCard] = []
        seen_ids: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
            )

            ok = await _load_cookies(context)
            if not ok:
                await browser.close()
                return []

            for role in roles:
                for location in locations:
                    logger.info(f"LinkedIn: scraping '{role}' in '{location}'")
                    fetched = await self._scrape_query(context, role, location, known_ids)
                    for job in fetched:
                        if job.id not in seen_ids:
                            seen_ids.add(job.id)
                            jobs.append(job)
                    logger.info(f"LinkedIn: {len(fetched)} jobs for '{role}' / '{location}'")

            await browser.close()

        logger.info(f"LinkedIn: total unique jobs = {len(jobs)}")
        return jobs

    async def _scrape_query(
        self, context: BrowserContext, role: str, location: str, known_ids: set
    ) -> List[JobCard]:
        list_page = await context.new_page()
        links = await _get_job_links(list_page, role, location, self.days_since_posted)
        await list_page.close()

        links = links[: self.max_jobs_per_query]
        jobs: List[JobCard] = []
        detail_page = await context.new_page()
        for link in links:
            if _make_job_id(link) in known_ids:
                continue  # already in DB — skip detail page fetch
            job = await _parse_job_detail(detail_page, link)
            if job:
                jobs.append(job)
        await detail_page.close()
        return jobs
