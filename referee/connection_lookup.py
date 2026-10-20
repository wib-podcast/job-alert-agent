"""Find a warm connection at the hiring company via fuzzy name matching."""
from __future__ import annotations

from typing import Optional, Dict, Any

from models import JobCard


def find_referee(job: JobCard, connections: list) -> Optional[Dict[str, Any]]:
    # TODO: implement fuzzy company matching with rapidfuzz
    raise NotImplementedError
