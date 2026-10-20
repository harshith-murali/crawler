import csv
import json
from unittest.mock import Mock

import pytest
import responses
from pydantic import ValidationError

from agent_crawler.config import Settings, load_settings
from agent_crawler.crawler import run
from agent_crawler.extraction import extract_records
from agent_crawler.http import BudgetExceeded, Skipped
from agent_crawler.models import FIELDS, Record, deduplicate, supported
from agent_crawler.output import write_outputs
from agent_crawler.parsing import parse_html
from agent_crawler.urls import in_scope, normalize_url, require_public_url

URL = "https://docs.example/"


def test_parse_title_text_links(html):
    page = parse_html(html, URL)
    assert page.title == "Illustrative AI agent inventory"
    assert "Support Agent" in page.text
    assert "ignoreThis" not in page.text
    assert ".hidden" not in page.text
    assert "https://docs.example/agents/next" in page.links


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "HTTPS://Docs.Example:443/a/../b?z=2&utm_source=x&a=1#part",
            "https://docs.example/b?a=1&z=2",
        ),
        ("/agents/./one", "https://docs.example/agents/one"),
        ("/a%2fb", "https://docs.example/a%2Fb"),
        ("mailto:test@example.com", None),
        ("https://user:pass@docs.example/", None),
        ("https://docs.example:8080/", None),
    ],
)
def test_normalize(raw, expected):
    assert normalize_url(raw, URL) == expected


def test_scope(settings):
    settings.url_prefixes = [URL + "agents"]
    assert in_scope(URL + "agents/a", settings)
    assert not in_scope(URL + "agents-other", settings)
    assert not in_scope("https://evil.example/agents", settings)
    assert not in_scope(URL + "agents/a.PDF", settings)
    settings.denied_prefixes = [URL + "agents/private"]
    assert not in_scope(URL + "agents/private/a", settings)


def test_extract(html):
    records = extract_records(parse_html(html, URL))
    assert len(records) == 4
    assert {r.evidence_status for r in records} == {
        "documented_deployed",
        "documented_experimental",
        "documented_proposed",
    }
    assert all(supported(r, parse_html(html, URL).text, URL) for r in records)
    assert (
        next(r for r in records if r.agent_name == "Research Assistant").task_or_purpose
        == "summarize public reports"
    )


def test_reject_generic_and_unstated():
    page = parse_html("<p>AI improves productivity.</p><p>Acme plans to explore agents.</p>", URL)
    assert extract_records(page) == []


def test_required_and_malformed(html):
    record = extract_records(parse_html(html, URL))[0].model_dump()
    for field in ("organization", "agent_name", "task_or_purpose", "supporting_evidence"):
        with pytest.raises(ValidationError):
            Record.model_validate(record | {field: " "})
    with pytest.raises(ValidationError):
        Record.model_validate(record | {"extra": "invented"})
    with pytest.raises(ValidationError):
        Record.model_validate(record | {"evidence_status": "verified"})
    assert not supported(
        Record.model_validate(record | {"task_or_purpose": "Invented"}),
        parse_html(html, URL).text,
        URL,
    )


def test_dedup_distinct_agents(html):
    records = extract_records(parse_html(html, URL))
    assert deduplicate(records + records) == records
    other = records[0].model_copy(update={"agent_name": "Other Agent"})
    assert len(deduplicate([records[0], other])) == 2


def test_csv_encoding_escaping_and_header(tmp_path, html):
    record = extract_records(parse_html(html, URL))[0].model_copy(
        update={"task_or_purpose": 'Answer "questions", including café\nfollow-ups'}
    )
    path, summary = write_outputs([record], {"records_extracted": 1}, tmp_path / "out.csv")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == FIELDS
        assert next(reader)["task_or_purpose"] == record.task_or_purpose
    assert json.loads(summary.read_text())["records_extracted"] == 1
    write_outputs([], {}, path)
    assert path.read_text().strip() == ",".join(FIELDS)


def robots(body="User-agent: *\nAllow: /", status=200):
    responses.get(URL + "robots.txt", body=body, status=status)


@responses.activate
def test_breadth_first_duplicates_depth_and_scope(settings, fetcher, html):
    robots()
    responses.get(
        URL,
        body='<a href="/one#x">One</a><a href="/one?utm_source=x">Dup</a>'
        '<a href="/asset.pdf">PDF</a><a href="https://outside.example/">Out</a>',
        content_type="text/html",
    )
    responses.get(URL + "one", body=html, content_type="text/html")
    settings.max_depth = 1
    records, stats = run(settings, fetcher=fetcher)
    assert len(records) == 4
    assert stats["pages_discovered"] == stats["pages_fetched"] == 2
    assert len(responses.calls) == 3  # robots cached
    assert stats["pages_failed"] == 0


@responses.activate
def test_max_pages(settings, fetcher):
    robots()
    responses.get(URL, body='<a href="/next">Next</a>', content_type="text/html")
    settings.max_pages = 1
    _, stats = run(settings, fetcher=fetcher)
    assert stats["pages_attempted"] == 1
    assert stats["stop_reason"] == "page_limit"


@responses.activate
def test_duplicate_content(settings, fetcher, html):
    robots()
    settings.seed_urls += [URL + "copy"]
    for url in settings.seed_urls:
        responses.get(url, body=html, content_type="text/html")
    settings.max_depth = 0
    records, stats = run(settings, fetcher=fetcher)
    assert len(records) == 4
    assert stats["duplicate_pages"] == 1


@responses.activate
def test_http_error_and_timeout(settings, fetcher):
    import requests

    robots()
    settings.seed_urls += [URL + "timeout"]
    responses.get(URL, status=500)
    responses.get(URL + "timeout", body=requests.Timeout())
    records, stats = run(settings, fetcher=fetcher)
    assert records == []
    assert stats["pages_failed"] == 2
    assert len(stats["errors"]) == 2


@responses.activate
def test_retry(fetcher, settings):
    robots()
    settings.retries = 1
    fetcher.sleeper = Mock()
    responses.get(URL, status=503)
    responses.get(URL, body="<p>ok</p>", content_type="text/html")
    assert fetcher.fetch(URL)[0] == URL
    assert fetcher.sleeper.called


@responses.activate
def test_robot_disallow(fetcher):
    robots("User-agent: *\nDisallow: /")
    with pytest.raises(Skipped):
        fetcher.fetch(URL)
    assert len(responses.calls) == 1


@responses.activate
def test_robot_unavailable_fails_closed(fetcher):
    robots(status=403)
    with pytest.raises(Skipped):
        fetcher.fetch(URL)


@responses.activate
def test_redirect_scope_checked(fetcher):
    robots()
    responses.get(URL, status=302, headers={"Location": "https://outside.example/"})
    with pytest.raises(Skipped):
        fetcher.fetch(URL)
    assert len(responses.calls) == 2


@responses.activate
def test_redirect_destination_robots(fetcher):
    robots("User-agent: *\nDisallow: /private")
    responses.get(URL, status=302, headers={"Location": "/private"})
    with pytest.raises(Skipped):
        fetcher.fetch(URL)


@responses.activate
def test_unsupported_and_oversize(fetcher, settings):
    robots()
    responses.get(URL, body="pdf", content_type="application/pdf")
    with pytest.raises(Skipped):
        fetcher.fetch(URL)
    responses.get(URL + "large", body="x" * 2048, content_type="text/html")
    settings.max_response_bytes = 1024
    with pytest.raises(Skipped):
        fetcher.fetch(URL + "large")


def test_runtime_budget(fetcher, settings):
    fetcher.deadline = 0
    records, stats = run(settings, fetcher=fetcher)
    assert not records
    assert stats["stop_reason"] == "runtime_limit"
    with pytest.raises(BudgetExceeded):
        fetcher.pause(1)


def test_no_optional_credentials(settings, fetcher, monkeypatch):
    from agent_crawler.providers import llm_records, search_urls

    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings.search_queries = ["AI agents"]
    settings.llm_provider = "json-http"
    assert search_urls(settings, fetcher) == []
    assert llm_records(None, settings, fetcher) == []


def test_empty_run(settings):
    settings.seed_urls = []
    records, stats = run(settings)
    assert not records and stats["pages_discovered"] == 0


def test_config_environment_overrides(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text('{"max_pages": 3}')
    monkeypatch.setenv("MAX_PAGES", "7")
    monkeypatch.setenv("SEED_URLS", '["https://docs.example/"]')
    settings = load_settings(str(path))
    assert settings.max_pages == 7
    assert settings.allowed_domains == ["docs.example"]
    with pytest.raises(ValidationError):
        Settings(max_pages=0)


def test_private_destination_rejected(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="non-public"):
        require_public_url("https://localhost/")


@responses.activate
def test_case_insensitive_headers_and_utf8(fetcher):
    robots()
    responses.add(
        responses.Response(
            method="GET",
            url=URL,
            body="<p>café — agent</p>".encode(),
            headers={"content-type": "text/html"},
            content_type=None,
        )
    )
    assert "café — agent" in fetcher.fetch(URL)[1]


@responses.activate
def test_invalid_charset_fallback(fetcher):
    robots()
    responses.add(
        responses.Response(
            method="GET",
            url=URL,
            body=b"<p>ok</p>",
            headers={"content-type": "text/html; charset=invalid-charset"},
            content_type=None,
        )
    )
    assert "ok" in fetcher.fetch(URL)[1]


@responses.activate
def test_robot_delay_and_request_rate(settings):
    from agent_crawler.http import Fetcher

    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    robots("User-agent: *\nAllow: /\nCrawl-delay: 3\nRequest-rate: 1/5")
    responses.get(URL, body="<p>ok</p>", content_type="text/html")
    f = Fetcher(settings, clock=lambda: now[0], sleeper=sleep, public_check=lambda _: None)
    try:
        f.fetch(URL)
        assert sleeps == [5]
    finally:
        f.close()


def test_dedup_same_relationship_different_status(html):
    original = extract_records(parse_html(html, URL))[0]
    additional = original.model_copy(update={"evidence_status": "documented_use_case"})
    assert deduplicate([original, additional]) == [original]


@responses.activate
def test_deterministic_findings_survive_llm_budget(settings, fetcher, html, monkeypatch):
    robots()
    responses.get(URL, body=html, content_type="text/html")
    settings.max_depth = 0

    def exhaust(*args):
        raise BudgetExceeded("runtime limit")

    monkeypatch.setattr("agent_crawler.crawler.llm_records", exhaust)
    records, stats = run(settings, fetcher=fetcher)
    assert len(records) == 4
    assert stats["stop_reason"] == "runtime_limit"


@responses.activate
def test_discovery_cap(settings, fetcher):
    robots()
    responses.get(URL, body='<a href="/a">A</a><a href="/b">B</a>', content_type="text/html")
    settings.max_discovered = 1
    _, stats = run(settings, fetcher=fetcher)
    assert stats["pages_discovered"] == 1
    assert stats["discovery_limit_reached"] is True
