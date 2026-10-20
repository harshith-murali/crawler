"""Review candidate sources with the same robots/access policy without replacing the inventory."""

import json
from pathlib import Path

from run_public_crawl import SnapshotFetcher

from agent_crawler.config import load_settings
from agent_crawler.http import FetchError


def main():
    settings = load_settings("config.finance-research.json")
    fetcher = SnapshotFetcher(settings, Path("output/research"))
    failures = []
    try:
        for url in settings.seed_urls:
            try:
                final, _ = fetcher.fetch(url)
                print(json.dumps({"url": final, "status": "fetched"}), flush=True)
            except (FetchError, ValueError, OSError) as exc:
                failures.append({"url": url, "reason": str(exc)})
                print(json.dumps(failures[-1]), flush=True)
    finally:
        fetcher.close()
        Path("output/research/failures.json").write_text(
            json.dumps(failures, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
