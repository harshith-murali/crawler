"""Check CSV schemas and exact evidence against the live run's retained source snapshots."""

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from agent_crawler.extraction import extract_records
from agent_crawler.models import Record, supported
from agent_crawler.parsing import parse_html


def main():
    folder = Path("output/sources")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    by_url = {item["source_url"]: item for item in manifest}
    checks = []
    with Path("output/agent_inventory.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            record = Record.model_validate(row)
            source = by_url[record.source_url]
            text = (folder / source["text_file"]).read_text(encoding="utf-8")
            # Hash saved bytes without newline conversion: this matches the original UTF-8 HTML.
            digest = hashlib.sha256((folder / source["html_file"]).read_bytes()).hexdigest()
            source_page = parse_html(
                (folder / source["html_file"]).read_bytes().decode("utf-8"), record.source_url
            )
            reproduced = any(
                r.model_dump() == record.model_dump() for r in extract_records(source_page)
            )
            checks.append(
                {
                    "agent_name": record.agent_name,
                    "organization": record.organization,
                    "source_url": record.source_url,
                    "evidence_matches_saved_source": supported(record, text, record.source_url),
                    "snapshot_hash_matches": digest == source["sha256_utf8_html"],
                    "record_and_status_reproduced_from_source": reproduced,
                    "evidence_status": record.evidence_status,
                }
            )
    passed = bool(checks) and all(
        c["evidence_matches_saved_source"]
        and c["snapshot_hash_matches"]
        and c["record_and_status_reproduced_from_source"]
        for c in checks
    )
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "records_checked": len(checks),
        "inventory_sha256": hashlib.sha256(
            Path("output/agent_inventory.csv").read_bytes()
        ).hexdigest(),
        "all_checks_passed": passed,
        "meaning": "Source text matching, not independent deployment verification",
        "records": checks,
    }
    Path("output/agent_inventory.evidence_check.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"rows": len(checks), "source_pages": len(manifest), "all_evidence_matches": passed}
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
