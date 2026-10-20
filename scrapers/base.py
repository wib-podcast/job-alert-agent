"""Abstract base class for all job scrapers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from models import JobCard


class BaseScraper(ABC):
    source: str = ""

    @abstractmethod
    async def scrape(self, roles: List[str], locations: List[str]) -> List[JobCard]:
        """Scrape jobs and return a list of JobCard objects."""
        ...
