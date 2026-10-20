"""Suggest bullet point edits for a specific job using Claude."""
from __future__ import annotations

from typing import List

from models import JobCard


async def tweak_bullets(job: JobCard, cv_text: str) -> List[str]:
    # TODO: implement bullet tweaking via Claude
    raise NotImplementedError
