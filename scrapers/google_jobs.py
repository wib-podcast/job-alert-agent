"""
Google Jobs scraper — Playwright targeting the Google Jobs SERP widget.

Navigates to google.com/search?q=<role>+jobs+<location>&ibp=htl;jobs
and extracts job cards from the embedded job listing panel.
No API key required; uses headless Chromium.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Page

from models import JobCard
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_BASE = "https://www.google.com"


def _make_job_id(url: str, title: str, company: str) -> str:
    key = f"google:{title}:{company}:{url}"
    return hashlib.sha1(key.encode()).hexdigest()


def _parse_posted_text(text: str) -> Optional[datetime]:
    """Convert 'Posted 3 days ago', '1 week ago', 'Today', etc. to datetime."""
    if not text:
        return None
    text = text.lower().strip()
    now = datetime.now(tz=timezone.utc)
    if "today" in text or "just now" in text or "hour" in text:
        m = re.search(r"(\d+)\s+hour", text)
        hours = int(m.group(1)) if m else 0
        return now - timedelta(hours=hours)
    m = re.search(r"(\d+)\s+day", text)
    if m:
        return now - timedelta(days=int(m.group(1)))
    m = re.search(r"(\d+)\s+week", text)
    if m:
        return now - timedelta(weeks=int(m.group(1)))
    m = re.search(r"(\d+)\s+month", text)
    if m:
        return now - timedelta(days=int(m.group(1)) * 30)
    return None


async def _scrape_google_jobs_page(page: Page, role: str, location: str, days: int) -> List[JobCard]:
    """Open Google Jobs SERP and extract job cards visible in the panel."""
    query = f"{role} jobs {location}"
    url = f"{_BASE}/search?q={quote_plus(query)}&ibp=htl;jobs"
    jobs: List[JobCard] = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(3000)
    except Exception as exc:
        logger.warning(f"Google Jobs page failed for '{role}' / '{location}': {exc}")
        return jobs

    # Accept cookie/consent prompts if present (EU regions)
    try:
        consent_btn = page.locator("button:has-text('Accept all'), button:has-text('I agree')")
        if await consent_btn.count() > 0:
            await consent_btn.first.click()
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    # Wait for the job cards panel to load
    try:
        await page.wait_for_selector('[jsname="MQCje"], .gws-plugins-horizon-jobs__li-ed, li[data-ved]', timeout=10_000)
    except Exception:
        logger.warning(f"Google Jobs panel not found for '{role}' / '{location}' — may be blocked or layout changed")
        return jobs

    # Scroll to load more cards
    for _ in range(5):
        await page.evaluate("window.scrollBy(0, 400)")
        await page.wait_for_timeout(600)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

    # Extract all job cards via JS evaluation
    raw_cards = await page.evaluate("""() => {
        const results = [];

        // Try multiple selectors for Google Jobs card containers
        const selectors = [
            'li[data-ved] .iFjolb',          // job title link containers
            '.gws-plugins-horizon-jobs__li-ed',  // full job list items
            '[jsname="MQCje"] li',            // jobs panel list items
        ];

        let cards = [];
        for (const sel of selectors) {
            cards = Array.from(document.querySelectorAll(sel));
            if (cards.length > 0) break;
        }

        for (const card of cards) {
            const get = (sel) => card.querySelector(sel)?.innerText?.trim() || '';

            const titleEl = card.querySelector('.BjJfJf, .iFjolb, [jsname="qdOxv"]');
            const companyEl = card.querySelector('.vNEEBe, .nJlQNd, [jsname="UK95Qe"]');
            const locationEl = card.querySelector('.Qk80Jf, .M4uis, [jsname="MfwMHb"]');
            const postedEl = card.querySelector('.SuWscb, .LL4CDc, [jsname="J4WVJe"]');
            const linkEl = card.querySelector('a[href]');

            const title = titleEl?.innerText?.trim() || '';
            const company = companyEl?.innerText?.trim() || '';
            const location = locationEl?.innerText?.trim() || '';
            const posted = postedEl?.innerText?.trim() || '';
            const href = linkEl?.href || '';

            if (title && company) {
                results.push({ title, company, location, posted, href });
            }
        }
        return results;
    }""")

    if not raw_cards:
        # Fallback: try clicking individual job cards to extract details
        logger.info(f"Google Jobs: no cards via JS eval for '{role}' / '{location}', trying click-through")
        raw_cards = await _scrape_via_click(page)

    cutoff_ts = cutoff.timestamp() if cutoff else None

    for card in raw_cards:
        title = card.get("title", "").strip()
        company = card.get("company", "").strip()
        if not title or not company:
            continue

        posted_text = card.get("posted", "")
        posted_date = _parse_posted_text(posted_text)

        # Filter by date if we got one
        if posted_date and cutoff_ts and posted_date.timestamp() < cutoff_ts:
            continue

        location_text = card.get("location", "")
        href = card.get("href", "")

        job = JobCard(
            id=_make_job_id(href, title, company),
            title=title,
            company=company,
            location=location_text,
            job_url=href or url,
            description="",  # Google Jobs doesn't expose full JD in the panel
            source="google_jobs",
            posted_date=posted_date,
        )
        jobs.append(job)

    logger.info(f"Google Jobs: {len(jobs)} jobs for '{role}' / '{location}'")
    return jobs


async def _scrape_via_click(page: Page) -> list:
    """Fallback: click each job card and scrape the detail panel."""
    results = []
    try:
        # Find clickable job card titles
        title_els = await page.query_selector_all('.BjJfJf, .iFjolb')
        for el in title_els[:20]:  # cap at 20 to avoid infinite loops
            try:
                await el.click()
                await page.wait_for_timeout(1000)
                data = await page.evaluate("""() => {
                    const get = sel => document.querySelector(sel)?.innerText?.trim() || '';
                    return {
                        title: get('[jsname="qdOxv"], .KLsYvd'),
                        company: get('[jsname="UK95Qe"], .vNEEBe'),
                        location: get('[jsname="MfwMHb"], .Qk80Jf'),
                        posted: get('[jsname="J4WVJe"], .SuWscb'),
                        href: document.querySelector('a.pMhGee, a[data-ved][href*="apply"]')?.href || window.location.href,
                    };
                }""")
                if data.get("title") and data.get("company"):
                    results.append(data)
            except Exception:
                continue
    except Exception as exc:
        logger.debug(f"Google Jobs click-through failed: {exc}")
    return results


class GoogleJobsScraper(BaseScraper):
    source = "google_jobs"

    def __init__(self, max_jobs_per_query: int = 20, days_since_posted: int = 14):
        self.max_jobs_per_query = max_jobs_per_query
        self.days_since_posted = days_since_posted

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
                ),
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="Asia/Kolkata",
            )
            page = await context.new_page()

            for role in roles:
                for location in locations:
                    logger.info(f"Google Jobs: scraping '{role}' in '{location}'")
                    fetched = await _scrape_google_jobs_page(
                        page, role, location, self.days_since_posted
                    )
                    fetched = fetched[: self.max_jobs_per_query]
                    for job in fetched:
                        if job.id not in seen_ids:
                            seen_ids.add(job.id)
                            jobs.append(job)

            await browser.close()

        logger.info(f"Google Jobs: total unique jobs = {len(jobs)}")
        return jobs
