"""
Naukri.com scraper — uses Playwright to bypass reCAPTCHA.

Loads the search page in a real browser, intercepts the JSON API response,
and parses job listings from it.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import List

from playwright.async_api import async_playwright, Response

from models import JobCard
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_BASE_SEARCH = "https://www.naukri.com"


def _make_job_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}:{url}".encode()).hexdigest()


def _parse_timestamp(ms: int | None) -> datetime | None:
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception:
        return None


def _parse_item(item: dict) -> JobCard | None:
    try:
        url = item.get("jdURL") or item.get("jobUrl") or ""
        if not url.startswith("http"):
            url = f"https://www.naukri.com{url}"

        title = item.get("title", "").strip()
        company = (item.get("companyName") or item.get("company") or "").strip()
        if not title or not company:
            return None

        location = ""
        for ph in item.get("placeholders", []):
            if ph.get("type") == "location":
                location = ph.get("label", "")
                break

        desc_parts = [item.get("jobDescription", "")]
        for ph in item.get("placeholders", []):
            if ph.get("type") == "experience":
                desc_parts.append(f"Experience: {ph.get('label', '')}")
        description = "\n".join(p for p in desc_parts if p).strip()

        skills = [s.get("label", "") for s in item.get("tagsAndSkills", []) if s.get("label")]
        if skills:
            description += f"\nSkills: {', '.join(skills)}"

        return JobCard(
            id=_make_job_id("naukri", url),
            title=title,
            company=company,
            location=location,
            job_url=url,
            description=description,
            source="naukri",
            posted_date=_parse_timestamp(item.get("createdDate")),
            must_have_skills=skills,
        )
    except Exception as exc:
        logger.debug(f"Failed to parse Naukri item: {exc}")
        return None


class NaukriScraper(BaseScraper):
    source = "naukri"

    def __init__(self, max_pages: int = 2):
        self.max_pages = max_pages

    async def scrape(self, roles: List[str], locations: List[str]) -> List[JobCard]:
        jobs: List[JobCard] = []
        seen_ids: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )

            for role in roles:
                for location in locations:
                    logger.info(f"Naukri: scraping '{role}' in '{location}'")
                    fetched = await self._scrape_query(context, role, location)
                    for job in fetched:
                        if job.id not in seen_ids:
                            seen_ids.add(job.id)
                            jobs.append(job)
                    logger.info(f"Naukri: {len(fetched)} jobs for '{role}' / '{location}'")

            await browser.close()

        logger.info(f"Naukri: total unique jobs = {len(jobs)}")
        return jobs

    async def _scrape_query(self, context, role: str, location: str) -> List[JobCard]:
        jobs: List[JobCard] = []
        page = await context.new_page()
        captured: list[dict] = []

        async def handle_response(response: Response) -> None:
            if "jobapi" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    items = data.get("jobDetails") or data.get("jobs") or []
                    captured.extend(items)
                except Exception:
                    pass

        page.on("response", handle_response)

        for page_no in range(1, self.max_pages + 1):
            role_slug = role.lower().replace(" ", "-")
            loc_slug = location.lower().replace(" ", "-")
            url = f"{_BASE_SEARCH}/{role_slug}-jobs-in-{loc_slug}-{page_no}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                logger.warning(f"Naukri page load failed: {exc}")
                break

        await page.close()

        for item in captured:
            job = _parse_item(item)
            if job:
                jobs.append(job)

        return jobs
