"""Regression checks for retaining lifecycle status and rejecting stale evidence reports."""

import hashlib
import json
from pathlib import Path

import pytest

from agent_crawler.extraction import extract_records
from agent_crawler.output import write_outputs
from agent_crawler.parsing import parse_html
from scripts.check_inventory_evidence import main as audit
from scripts.export_finance_views import main as export_views


def setup_inventory(tmp_path, monkeypatch):
    cases = json.loads(
        (Path(__file__).parent / "fixtures/finance_excerpts.json").read_text(encoding="utf-8")
    )
    case = next(c for c in cases if c["agent_name"] == "CSO Assistant")
    html = "\n\n".join(case["source_excerpts"])
    page = parse_html(html, case["source_url"])
    record = next(r for r in extract_records(page) if r.agent_name == "CSO Assistant")
    monkeypatch.chdir(tmp_path)
    folder = Path("output/sources")
    folder.mkdir(parents=True)
    (folder / "source.html").write_text(html, encoding="utf-8")
    (folder / "source.txt").write_text(page.text, encoding="utf-8")
    (folder / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "source_url": page.url,
                    "html_file": "source.html",
                    "text_file": "source.txt",
                    "sha256_utf8_html": hashlib.sha256(html.encode()).hexdigest(),
                }
            ]
        ),
        encoding="utf-8",
    )
    Path("config.finance.json").write_text(json.dumps({"seed_urls": [page.url]}), encoding="utf-8")
    write_outputs([record], {}, "output/agent_inventory.csv")
    return record


def test_audit_accepts_source_reproduced_pilot(tmp_path, monkeypatch):
    setup_inventory(tmp_path, monkeypatch)
    audit()
    check = json.loads(Path("output/agent_inventory.evidence_check.json").read_text())
    assert check["all_checks_passed"] is True
    assert check["records"][0]["record_and_status_reproduced_from_source"] is True
    export_views()
    # A documented pilot must not enter the deployment-only view.
    assert len(Path("output/financial_services_deployments.csv").read_text().splitlines()) == 1
    assert "CSO Assistant" in Path("output/financial_services_pilots.csv").read_text()


def test_audit_rejects_manual_promotion_of_pilot(tmp_path, monkeypatch):
    record = setup_inventory(tmp_path, monkeypatch)
    write_outputs(
        [record.model_copy(update={"evidence_status": "documented_deployed"})],
        {},
        "output/agent_inventory.csv",
    )
    with pytest.raises(SystemExit):
        audit()
    check = json.loads(Path("output/agent_inventory.evidence_check.json").read_text())
    assert check["all_checks_passed"] is False
    assert check["records"][0]["evidence_matches_saved_source"] is True
    assert check["records"][0]["record_and_status_reproduced_from_source"] is False


def test_views_reject_stale_audit_with_same_record_count(tmp_path, monkeypatch):
    record = setup_inventory(tmp_path, monkeypatch)
    audit()
    write_outputs(
        [record.model_copy(update={"evidence_status": "documented_deployed"})],
        {},
        "output/agent_inventory.csv",
    )
    with pytest.raises(SystemExit, match="evidence"):
        export_views()
