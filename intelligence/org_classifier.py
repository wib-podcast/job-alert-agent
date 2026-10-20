"""Classify org stage (Seed, Series A-B, Series C+, Public, Enterprise)."""
from __future__ import annotations

from models import JobCard


async def classify_org(job: JobCard) -> JobCard:
    # TODO: implement org stage classification via Crunchbase + Claude
    raise NotImplementedError
