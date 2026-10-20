"""Derive deployment/pilot/capability views from the evidence-checked inventory, without new claims."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from agent_crawler.models import Record
from agent_crawler.output import write_outputs
from agent_crawler.urls import normalize_url


def main():
    source_config = json.loads(Path("config.finance.json").read_text(encoding="utf-8"))
    finance_urls = {normalize_url(url) for url in source_config["seed_urls"]}
    with Path("output/agent_inventory.csv").open(encoding="utf-8", newline="") as stream:
        records = [Record.model_validate(row) for row in csv.DictReader(stream)]
    check = json.loads(
        Path("output/agent_inventory.evidence_check.json").read_text(encoding="utf-8")
    )
    if (
        not check["all_checks_passed"]
        or check["records_checked"] != len(records)
        or check.get("inventory_sha256")
        != hashlib.sha256(Path("output/agent_inventory.csv").read_bytes()).hexdigest()
    ):
        raise SystemExit(
            "Run scripts/check_inventory_evidence.py successfully before exporting views"
        )
    financial = [r for r in records if r.source_url in finance_urls]
    outputs = {
        "financial_services_inventory": financial,
        "financial_services_deployments": [
            r for r in financial if r.evidence_status == "documented_deployed"
        ],
        "financial_services_pilots": [
            r for r in financial if r.evidence_status == "documented_experimental"
        ],
        "product_capabilities": [r for r in records if r.evidence_status == "documented_use_case"],
    }
    for name, rows in outputs.items():
        write_outputs(
            rows,
            {
                "derived_from": "output/agent_inventory.csv",
                "not_a_separate_crawl": True,
                "records_extracted": len(rows),
                "organizations": sorted({r.organization for r in rows}),
                "evidence_status_counts": dict(Counter(r.evidence_status for r in rows)),
            },
            f"output/{name}.csv",
        )
    summary = {
        "total_records": len(records),
        "financial_services_records": len(financial),
        "financial_services_organizations": sorted({r.organization for r in financial}),
        "financial_services_status_counts": dict(Counter(r.evidence_status for r in financial)),
        "overall_status_counts": dict(Counter(r.evidence_status for r in records)),
        "caution": "Statuses describe dated public documentation; not independent current-deployment verification.",
    }
    Path("output/inventory_breakdown.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
