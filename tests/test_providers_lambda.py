import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import responses

from agent_crawler.extraction import extract_records, status_from_text
from agent_crawler.parsing import parse_html
from agent_crawler.providers import llm_records, search_urls

URL = "https://docs.example/"
ENDPOINT = "https://gateway.example/extract"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("not deployed", "documented_use_case"),
        ("never uses this agent", "documented_use_case"),
        ("Deployed", "documented_deployed"),
        ("Pilot", "documented_experimental"),
        ("Proposed", "documented_proposed"),
    ],
)
def test_lifecycle_no_keyword_guess(text, expected):
    assert status_from_text(text) == expected


def test_human_agent_context_rejected():
    assert (
        extract_records(
            parse_html("<p>Illustrative Bank uses its Support Agent to answer questions.</p>", URL)
        )
        == []
    )


@responses.activate
def test_brave_returns_urls(settings, fetcher, monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    settings.search_queries = ["named AI agents"]
    responses.get(
        "https://api.search.brave.com/res/v1/web/search",
        json={"web": {"results": [{"url": URL}, {"url": None}, {}]}},
    )
    assert search_urls(settings, fetcher) == [URL]
    assert responses.calls[0].request.headers["X-Subscription-Token"] == "test-token"


@responses.activate
def test_search_failure_fallback(settings, fetcher, monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    settings.search_queries = ["agents"]
    responses.get("https://api.search.brave.com/res/v1/web/search", status=401)
    assert search_urls(settings, fetcher) == []


@responses.activate
def test_llm_valid_and_unsupported(settings, fetcher, monkeypatch, html):
    monkeypatch.setenv("LLM_API_KEY", "test-token")
    monkeypatch.setattr("agent_crawler.providers.require_public_url", lambda _: None)
    settings.llm_provider = "json-http"
    settings.llm_endpoint = ENDPOINT
    page = parse_html(html, URL)
    record = extract_records(page)[0].model_dump()
    responses.post(ENDPOINT, json={"records": [record]})
    result = llm_records(page, settings, fetcher)
    assert len(result) == 1
    assert result[0].evidence_status == "documented_use_case"
    sent = json.loads(responses.calls[0].request.body)
    assert sent["document"]["source_url"] == URL
    assert sent["response_schema"]["additionalProperties"] is False
    for update in (
        {"task_or_purpose": "fabricated task"},
        {"source_url": "https://other.example/"},
        {"supporting_evidence": "invented quote"},
    ):
        responses.post(ENDPOINT, json={"records": [record | update]})
        assert llm_records(page, settings, fetcher) == []


@responses.activate
def test_llm_schema_rejects_extra_and_wrong_types(settings, fetcher, monkeypatch, html):
    monkeypatch.setenv("LLM_API_KEY", "test-token")
    monkeypatch.setattr("agent_crawler.providers.require_public_url", lambda _: None)
    settings.llm_provider = "json-http"
    settings.llm_endpoint = ENDPOINT
    page = parse_html(html, URL)
    record = extract_records(page)[0].model_dump()
    for data in [
        {"records": [record], "execute": "bad"},
        {"records": [record | {"agent_name": 123}]},
        {"records": [record | {"evidence_status": "verified"}]},
        {"records": [{}]},
    ]:
        responses.post(ENDPOINT, json=data)
        assert llm_records(page, settings, fetcher) == []


def test_lambda_uploads_unique_artifacts_and_cleans(monkeypatch):
    from agent_crawler.lambda_handler import handler

    monkeypatch.setenv("SEED_URLS", "[]")
    monkeypatch.setenv("RESULTS_BUCKET", "test-bucket")
    s3 = Mock()
    captured = []

    def upload(filename, bucket, key, ExtraArgs):
        captured.append((Path(filename).read_text(), bucket, key, ExtraArgs))

    s3.upload_file.side_effect = upload
    monkeypatch.setattr("agent_crawler.lambda_handler.boto3.client", lambda service: s3)
    context = Mock()
    context.get_remaining_time_in_millis.return_value = 60000
    result = handler({"seed_urls": ["https://ignored.example/"]}, context)
    assert result["summary"]["records_extracted"] == 0
    assert result["summary"]["pages_discovered"] == 0
    assert result["csv_key"].startswith("runs/")
    assert len(captured) == 2
    assert captured[0][0].startswith("organization,task_or_purpose")
    assert captured[0][1] == "test-bucket"
    assert not Path(result["summary"]["output_file"]).exists()
    second = handler({}, context)
    assert result["csv_key"] != second["csv_key"]


def test_lambda_upload_failure_is_not_success(monkeypatch):
    from agent_crawler.lambda_handler import handler

    monkeypatch.setenv("SEED_URLS", "[]")
    monkeypatch.setenv("RESULTS_BUCKET", "test-bucket")
    s3 = Mock()
    s3.upload_file.side_effect = RuntimeError("upload failed")
    monkeypatch.setattr("agent_crawler.lambda_handler.boto3.client", lambda service: s3)
    context = Mock()
    context.get_remaining_time_in_millis.return_value = 60000
    with pytest.raises(RuntimeError, match="upload failed"):
        handler({}, context)


@responses.activate
def test_provider_size_limit(settings, fetcher, monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-token")
    settings.max_response_bytes = 1024
    settings.search_queries = ["agents"]
    responses.get("https://api.search.brave.com/res/v1/web/search", body="x" * 2048)
    assert search_urls(settings, fetcher) == []
