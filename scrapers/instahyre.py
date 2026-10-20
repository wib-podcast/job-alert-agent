"""Instahyre scraper — uses Playwright (JS-heavy SPA)."""
from __future__ import annotations

from typing import List

from models import JobCard
from scrapers.base import BaseScraper


class InstaHyreScraper(BaseScraper):
    source = "instahyre"

    async def scrape(self, roles: List[str], locations: List[str]) -> List[JobCard]:
        # TODO: implement Playwright-based Instahyre scraping
        raise NotImplementedError
