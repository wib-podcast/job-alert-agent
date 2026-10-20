"""
IIMJobs.com scraper — uses Playwright to render the React SPA.

Strategy:
1. Navigate to search results page for each role (location filter applied via URL param)
2. Wait for job cards to render, collect all job links (a[href*="/j/"])
3. For each job link, visit the detail page and extract title, company, location, description
"""
from __future__ import annotations

import hashlib
import logging
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Page

from models import JobCard
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_BASE = "https://www.iimjobs.com"


def _make_job_id(url: str) -> str:
    return hashlib.sha1(f"iimjobs:{url}".encode()).hexdigest()


def _build_search_url(role: str, location: str) -> str:
    role_slug = quote_plus(role.replace(" ", "+"))
    if location and location.lower() not in ("", "india", "remote"):
        return f"{_BASE}/search/{role_slug}?searchCity={quote_plus(location)}"
    return f"{_BASE}/search/{role_slug}"


async def _extract_job_links(page: Page, url: str) -> List[str]:
    """Navigate to search results and return all unique job detail URLs."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
    except Exception as exc:
        logger.warning(f"IIMJobs search page load failed: {exc}")
        return []

    # Scroll to trigger lazy loading
    for _ in range(3):
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(800)

    links = await page.eval_on_selector_all(
        "a[href*='/j/']",
        "els => els.map(e => e.href)"
    )
    # Deduplicate and filter out non-job links
    seen = set()
    result = []
    for link in links:
        link = link.split("?")[0]  # strip query params
        if "/j/" in link and link not in seen:
            seen.add(link)
            result.append(link)
    logger.info(f"IIMJobs: found {len(result)} job links at {url}")
    return result


async def _parse_job_page(page: Page, url: str) -> Optional[JobCard]:
    """Visit a job detail page and extract structured data."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
    except Exception as exc:
        logger.debug(f"IIMJobs detail page failed ({url}): {exc}")
        return None

    try:
        # Title: h1 is most reliable
        # IIMJobs h1 format: "CompanyName - Job Title" or just "Job Title"
        raw_title = ""
        h1 = await page.query_selector("h1")
        if h1:
            raw_title = (await h1.inner_text()).strip()

        if not raw_title:
            return None

        # Company name — try CSS selectors first
        company = ""
        for sel in [
            "[class*='company']",
            "[class*='Company']",
            "h2 a",
            "[data-testid*='company']",
        ]:
            el = await page.query_selector(sel)
            if el:
                company = (await el.inner_text()).strip()
                if company and company.lower() != "iimjobs.com":
                    break
                else:
                    company = ""

        # Fallback: IIMJobs page title is "CompanyName - Job Title | iimjobs.com"
        # So parts[0] of the "|" split gives "CompanyName - Job Title"
        # and the company is the first segment before " - "
        if not company:
            page_title = await page.title()
            left = page_title.split("|")[0].strip()  # "CompanyName - Job Title"
            parts = left.split(" - ", 1)
            if len(parts) == 2:
                # Heuristic: company is the first part if it looks like a proper noun
                # (doesn't start with common job-title words)
                _job_words = {"senior", "associate", "lead", "principal", "head", "vp",
                              "director", "manager", "analyst", "product", "group"}
                candidate = parts[0].strip()
                if candidate.lower().split()[0] not in _job_words:
                    company = candidate

        # Parse clean title: strip company prefix if present ("Meesho - PM" → "PM")
        if company and raw_title.startswith(company + " - "):
            title = raw_title[len(company) + 3:].strip()
        else:
            title = raw_title

        # Location
        location = ""
        for sel in [
            "[class*='location']",
            "[class*='Location']",
            "[data-testid*='location']",
        ]:
            el = await page.query_selector(sel)
            if el:
                location = (await el.inner_text()).strip()
                if location:
                    break

        # Description — grab the biggest text block available
        description = ""
        for sel in [
            "[class*='job-desc']",
            "[class*='jobDesc']",
            "[class*='description']",
            "article",
            "main",
        ]:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.inner_text()).strip()
                if len(txt) > len(description):
                    description = txt

        # Cap description to avoid token blowout in scorer
        description = description[:4000]

        return JobCard(
            id=_make_job_id(url),
            title=title,
            company=company or "Unknown",
            location=location,
            job_url=url,
            description=description,
            source="iimjobs",
        )

    except Exception as exc:
        logger.debug(f"IIMJobs parse error ({url}): {exc}")
        return None


class IIMJobsScraper(BaseScraper):
    source = "iimjobs"

    def __init__(self, max_jobs_per_query: int = 30, days_since_posted: int = 14):
        self.max_jobs_per_query = max_jobs_per_query
        self.days_since_posted = days_since_posted

    async def scrape(self, roles: List[str], locations: List[str], dsn: str = None) -> List[JobCard]:
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
                viewport={"width": 1280, "height": 800},
            )

            for role in roles:
                for location in locations:
                    logger.info(f"IIMJobs: scraping '{role}' in '{location}'")
                    fetched = await self._scrape_query(context, role, location, known_ids)
                    for job in fetched:
                        if job.id not in seen_ids:
                            seen_ids.add(job.id)
                            jobs.append(job)
                    logger.info(
                        f"IIMJobs: {len(fetched)} jobs for '{role}' / '{location}'"
                    )

            await browser.close()

        logger.info(f"IIMJobs: total unique jobs = {len(jobs)}")
        return jobs

    async def _scrape_query(
        self, context, role: str, location: str, known_ids: set
    ) -> List[JobCard]:
        search_url = _build_search_url(role, location)

        list_page = await context.new_page()
        job_links = await _extract_job_links(list_page, search_url)
        await list_page.close()

        job_links = job_links[: self.max_jobs_per_query]

        jobs: List[JobCard] = []
        detail_page = await context.new_page()
        for link in job_links:
            if _make_job_id(link) in known_ids:
                continue  # already in DB — skip detail page fetch
            job = await _parse_job_page(detail_page, link)
            if job:
                jobs.append(job)
        await detail_page.close()

        return jobs
