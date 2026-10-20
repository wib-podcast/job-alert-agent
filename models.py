from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class JobCard(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    id: str = Field(..., description="Stable hash: sha1(source + job_url)")
    title: str
    company: str
    location: str
    geo: str = Field(
        default="IN",
        description="ISO 3166-1 alpha-2, uppercase: AE SG GB IE TH MY VN IN",
    )
    job_url: str
    description: str = ""
    source: str = Field(..., description="linkedin | naukri | iimjobs | instahyre")

    # ── Timing ────────────────────────────────────────────────────────────────
    posted_date: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # ── Intelligence layer (populated after LLM scoring) ──────────────────────
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="0–10 relevance score from the LLM scorer",
    )
    role_type: Optional[str] = Field(
        default=None,
        description="e.g. IC, Manager, Director, VP",
    )
    org_stage: Optional[str] = Field(
        default=None,
        description="e.g. Seed, Series A-B, Series C+, Public, Enterprise",
    )

    # ── CV layer ─────────────────────────────────────────────────────────────
    recommended_cv: Optional[str] = Field(
        default=None,
        description="Filename of the best-fit CV variant",
    )
    cv_tweaks: List[str] = Field(
        default_factory=list,
        description="Suggested bullet edits for this specific job",
    )

    # ── Referee ───────────────────────────────────────────────────────────────
    referee: Optional[Dict[str, Any]] = Field(
        default=None,
        description="{'name': str, 'role': str, 'linkedin_url': str} or None",
    )

    # ── Skills gap ────────────────────────────────────────────────────────────
    must_have_skills: List[str] = Field(
        default_factory=list,
        description="Required skills extracted from JD",
    )
    resume_gaps: List[str] = Field(
        default_factory=list,
        description="Skills in must_have_skills missing from the candidate CV",
    )

    # ── State ─────────────────────────────────────────────────────────────────
    alerted: bool = Field(
        default=False,
        description="True once this job has been included in a sent digest",
    )

    @field_validator("geo")
    @classmethod
    def _upper_geo(cls, v: str) -> str:
        """A scraper knows which country it queried; casing varies. Fold it."""
        return (v or "IN").strip().upper()

    class Config:
        # Allow extra fields from scrapers without crashing
        extra = "ignore"
