"""Reviewed official excerpts are regression inputs, not synthetic inventory output."""

import json
from pathlib import Path

import pytest

from agent_crawler.extraction import extract_records
from agent_crawler.models import evidence_in_source, supported
from agent_crawler.parsing import parse_html

CASES = json.loads(
    (Path(__file__).parent / "fixtures/finance_excerpts.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["agent_name"])
def test_reviewed_source_relationships_and_status(case):
    text = "\n\n".join(case["source_excerpts"])
    page = parse_html(text, case["source_url"])
    found = [r for r in extract_records(page) if r.agent_name == case["agent_name"]]
    assert len(found) == 1
    record = found[0]
    assert record.organization == case["organization"]
    assert record.task_or_purpose == case["task_or_purpose"]
    assert record.evidence_status == case["evidence_status"]
    assert supported(record, page.text, page.url)
    assert extract_records(parse_html(text, "https://unreviewed.example/")) == []


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["agent_name"])
def test_absent_disclosure_emits_no_stored_finding(case):
    assert extract_records(parse_html("Documentation unavailable.", case["source_url"])) == []


@pytest.mark.parametrize(
    "before,after,name",
    [
        (
            "Through the rollout, colleagues have access",
            "We plan a rollout so colleagues might have access",
            "Citi Assist",
        ),
        ("is now live in Cora", "is not live in Cora", "Fraud Triage Agent"),
        ("is now live in Cora", "may eventually be live in Cora", "Fraud Triage Agent"),
        ("is used today", "may be used someday", "Erica for Employees"),
        ("we became the first to roll out", "we plan to roll out", "OCBC GPT"),
        ("how we use Aiden", "how we might use Aiden", "Aiden"),
        ("has answered millions of user queries", "may answer user queries", "Finn"),
        ("we have implemented AI", "we may implement AI", "OCBC Buddy"),
        (
            "has now supported customers through more than 1 billion interactions",
            "might support customers eventually",
            "Fargo",
        ),
    ],
)
def test_future_or_negated_lifecycle_not_promoted(before, after, name):
    case = next(case for case in CASES if case["agent_name"] == name)
    text = "\n\n".join(case["source_excerpts"])
    assert before in text
    found = extract_records(parse_html(text.replace(before, after), case["source_url"]))
    assert all(r.agent_name != name for r in found)


def test_pilots_and_announced_capability_are_separate_from_deployment():
    statuses = {case["agent_name"]: case["evidence_status"] for case in CASES}
    assert statuses["CSO Assistant"] == "documented_experimental"
    assert statuses["Cora"] == "documented_experimental"
    assert statuses["AI Teammate"] == "documented_use_case"
    assert statuses["Fraud Triage Agent"] == "documented_deployed"


@pytest.mark.parametrize(
    "evidence,expected",
    [
        ("first quotation […] second quotation", True),
        ("second quotation […] first quotation", False),
        ("first quotation […] invented quotation", False),
        ("first quotation […] ", False),
        ("first quotation", True),
    ],
)
def test_noncontiguous_quotes_must_exist_in_order(evidence, expected):
    assert (
        evidence_in_source(
            evidence, "first quotation followed by omitted text and second quotation"
        )
        is expected
    )
