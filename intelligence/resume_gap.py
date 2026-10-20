"""Identify skills in the JD missing from the candidate's CV."""
from __future__ import annotations

from models import JobCard


async def analyse_gaps(job: JobCard, cv_text: str) -> JobCard:
    # TODO: implement gap analysis via Claude
    raise NotImplementedError
