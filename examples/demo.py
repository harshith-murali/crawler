from pathlib import Path

from agent_crawler.extraction import extract_records
from agent_crawler.output import write_outputs
from agent_crawler.parsing import parse_html


def main():
    folder = Path(__file__).parent
    page = parse_html(
        (folder / "illustrative_input.html").read_text(encoding="utf-8"),
        "https://illustrative.example/agents",
    )
    records = extract_records(page)
    write_outputs(
        records,
        {"illustrative_only": True, "records_extracted": len(records)},
        folder / "illustrative_agent_inventory.csv",
    )
    print(f"Wrote {len(records)} fictional illustrative records in examples/")


if __name__ == "__main__":
    main()
