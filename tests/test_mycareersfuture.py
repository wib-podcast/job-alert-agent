"""
Tests for the MyCareersFuture parser.

`to_job_card` and `strip_html` are pure, so they're tested against a recorded
fixture (tests/fixtures/mcf_search.json) rather than the live API — a portal
being down must not turn into a red build. The network path itself can only be
verified by running the scraper, which is what AGENTS.md asks for in the PR.
"""
from __future__ import annotations

import json
import pathlib
from datetime import timezone

from scrapers.mycareersfuture import _make_job_id, strip_html, to_job_card

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "mcf_search.json"
RESULTS = json.loads(FIXTURE.read_text())["results"]


def test_every_fixture_result_converts_to_a_job_card():
    cards = [to_job_card(r) for r in RESULTS]
    assert all(c is not None for c in cards)
    assert len(cards) == len(RESULTS)


def test_cards_are_tagged_singapore():
    """Geography comes from the scraper, never inferred from a location string."""
    for result in RESULTS:
        card = to_job_card(result)
        assert card.geo == "SG"
        assert card.location == "Singapore"


def test_the_id_is_derived_from_the_portal_uuid_and_is_stable():
    card = to_job_card(RESULTS[0])
    assert card.id == _make_job_id(RESULTS[0]["uuid"])
    assert to_job_card(RESULTS[0]).id == card.id


def test_a_result_without_a_title_or_uuid_is_dropped():
    """A job we can't identify can't be deduplicated, so it must not be stored."""
    assert to_job_card({"uuid": "x", "title": ""}) is None
    assert to_job_card({"title": "Product Manager"}) is None


def test_the_canonical_portal_url_is_preferred():
    card = to_job_card(RESULTS[0])
    expected = RESULTS[0]["metadata"]["jobDetailsUrl"]
    assert card.job_url == expected


def test_a_missing_details_url_falls_back_to_one_built_from_the_uuid():
    """Otherwise the posting reaches the digest with no link at all."""
    result = {"uuid": "abc", "title": "PM", "metadata": {}}
    assert to_job_card(result).job_url.endswith("/abc")


def test_an_undisclosed_employer_still_produces_a_card():
    """isHideHiringEmployerName postings are real jobs placed through agencies."""
    result = {"uuid": "abc", "title": "PM", "postedCompany": {}}
    assert to_job_card(result).company == "Undisclosed"


def test_shouty_company_names_are_title_cased():
    result = {"uuid": "a", "title": "PM", "postedCompany": {"name": "ACME PTE. LTD."}}
    assert to_job_card(result).company == "Acme Pte. Ltd."


def test_a_salary_range_is_surfaced_for_the_scorer():
    result = {
        "uuid": "a",
        "title": "PM",
        "salary": {"minimum": 8000, "maximum": 12000, "type": {"salaryType": "Monthly"}},
    }
    assert "SGD 8,000–12,000 monthly" in to_job_card(result).description


def test_a_missing_salary_is_simply_absent():
    result = {"uuid": "a", "title": "PM", "salary": {}}
    assert to_job_card(result).description == ""


def test_the_posting_date_is_parsed_as_utc():
    card = to_job_card(RESULTS[0])
    assert card.posted_date is not None
    assert card.posted_date.tzinfo == timezone.utc


def test_an_unparseable_posting_date_is_none_rather_than_a_crash():
    result = {"uuid": "a", "title": "PM", "metadata": {"newPostingDate": "not-a-date"}}
    assert to_job_card(result).posted_date is None


def test_detail_description_is_merged_in_as_plain_text():
    result = {"uuid": "a", "title": "PM"}
    detail = {"description": "<p>Build things</p><p>Ship them</p>", "minimumYearsExperience": 7}
    card = to_job_card(result, detail)
    assert "Minimum experience: 7 years" in card.description
    assert "Build things" in card.description
    assert "<p>" not in card.description


def test_descriptions_are_capped_so_one_posting_cannot_blow_the_token_budget():
    detail = {"description": "<p>" + ("word " * 5000) + "</p>"}
    card = to_job_card({"uuid": "a", "title": "PM"}, detail)
    assert len(card.description) <= 4000


class TestStripHtml:
    def test_block_tags_become_newlines_so_structure_survives(self):
        assert strip_html("<p>One</p><p>Two</p>") == "One\nTwo"

    def test_list_items_are_kept_on_separate_lines(self):
        assert strip_html("<ul><li>A</li><li>B</li></ul>") == "A\nB"

    def test_runs_of_blank_lines_are_collapsed(self):
        """Nested block tags otherwise leave big gaps that cost tokens."""
        assert strip_html("<div><p>One</p></div><div><p>Two</p></div>") == "One\n\nTwo"

    def test_entities_are_decoded(self):
        assert strip_html("<p>R&amp;D</p>") == "R&D"

    def test_empty_and_none_are_handled(self):
        assert strip_html(None) == ""
        assert strip_html("") == ""
