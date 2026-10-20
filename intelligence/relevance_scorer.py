"""
Score job relevance (0–10) using Claude — batched for cost efficiency.

Sends up to BATCH_SIZE jobs per API call instead of one-at-a-time.
Result: ~10× fewer API calls, ~5× cheaper model (Haiku) = ~50× cost reduction.
"""
from __future__ import annotations

import json
import logging
from typing import List

import anthropic

from config import cfg
from models import JobCard

logger = logging.getLogger(__name__)

BATCH_SIZE = 10  # jobs per Claude call

_client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

_SYSTEM = """\
You are a job relevance analyst. Score job postings for a candidate with a Product Management \
and Strategy background. Return structured JSON only — no markdown, no prose.
"""

_PROMPT_TEMPLATE = """\
Score these {n} job postings for a PM/Strategy candidate.
Target roles: {target_roles}
Preferred locations: {target_locations}

Scoring guide:
9-10: Perfect fit — title exactly matches a target role, location matches one of the preferred cities
7-8 : Good fit — PM, Growth, Strategy, or AI Strategy role; minor location/seniority mismatch or remote
5-6 : Partial — adjacent role (PMM, Business Analyst, Consultant, Ops) or significant seniority stretch
3-4 : Weak — tangentially related (e.g. sales, engineering with PM overlap)
0-2 : Irrelevant — completely wrong function (pure engineering, finance, HR, etc.)

Note: "AI Solutioning", "AI Strategy", "Growth Manager", "Strategy Manager" are all high-value target roles — score them 8–10 if the seniority fits.

{jobs_block}

Return a JSON array with exactly {n} objects, one per job in order:
[
  {{"i": 1, "relevance_score": 8.5, "role_type": "IC", "must_have_skills": ["skill1", "skill2"], "reasoning": "short"}},
  ...
]
role_type: IC | Manager | Director | VP | Unknown
reasoning: max 10 words
"""


def _jobs_block(jobs: List[JobCard]) -> str:
    lines = []
    for i, job in enumerate(jobs, 1):
        desc = (job.description or "")[:400]  # short excerpt per job
        lines.append(
            f"Job {i}:\n"
            f"  Title: {job.title}\n"
            f"  Company: {job.company}\n"
            f"  Location: {job.location}\n"
            f"  Description: {desc}"
        )
    return "\n\n".join(lines)


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def score_relevance_batch(jobs: List[JobCard]) -> List[JobCard]:
    """
    Score a list of jobs in batches of BATCH_SIZE.
    Returns jobs with relevance_score, role_type, must_have_skills populated.
    """
    results = []
    for start in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[start : start + BATCH_SIZE]
        scored = await _score_batch(batch)
        results.extend(scored)
    return results


async def _score_batch(jobs: List[JobCard]) -> List[JobCard]:
    prompt = _PROMPT_TEMPLATE.format(
        n=len(jobs),
        target_roles=", ".join(cfg.target_roles),
        target_locations=", ".join(cfg.target_locations),
        jobs_block=_jobs_block(jobs),
    )

    try:
        response = _client.messages.create(
            model=cfg.llm_model,
            max_tokens=BATCH_SIZE * 120,  # ~120 tokens per job result
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _strip_fences(response.content[0].text.strip())
        results = json.loads(text)

        # Map results back to jobs by index
        for item in results:
            idx = int(item.get("i", 0)) - 1
            if 0 <= idx < len(jobs):
                jobs[idx] = jobs[idx].model_copy(
                    update={
                        "relevance_score": float(item.get("relevance_score", 0.0)),
                        "role_type": item.get("role_type", "Unknown"),
                        "must_have_skills": item.get("must_have_skills", jobs[idx].must_have_skills),
                    }
                )
                logger.info(
                    f"Scored [{jobs[idx].relevance_score:.1f}/10] {jobs[idx].title}"
                    f" @ {jobs[idx].company} — {item.get('reasoning', '')}"
                )

    except json.JSONDecodeError as exc:
        logger.warning(f"Claude returned invalid JSON for batch starting at job 1: {exc}")
    except anthropic.APIError as exc:
        logger.error(f"Anthropic API error for batch: {exc}")

    return jobs


# Keep single-job interface for backwards compatibility
async def score_relevance(job: JobCard) -> JobCard:
    results = await score_relevance_batch([job])
    return results[0]
