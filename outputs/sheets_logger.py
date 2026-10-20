"""Log new jobs to Google Sheets via gspread."""
from __future__ import annotations

from typing import List

from models import JobCard


def log_to_sheets(jobs: List[JobCard]) -> None:
    # TODO: implement Google Sheets logging via gspread
    raise NotImplementedError
