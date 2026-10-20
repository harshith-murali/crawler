"""Inspect additional official sources without writing production records."""

import json
from pathlib import Path

from run_public_crawl import SnapshotFetcher

from agent_crawler.config import Settings
from agent_crawler.http import FetchError

urls = [
    "https://www.morganstanley.com/press-releases/ai-at-morgan-stanley-debrief-launch",
    "https://www.dbs.com/media/features/i-went-from-answering-calls-to-testing-ai.page",
    "https://www.natwestgroup.com/news-and-insights/latest-stories/ai-and-data/2025/jul/how-natwest-group-is-accelerating-opportunities-to-better-serve-.html",
    "https://www.natwestgroup.com/who-we-are/about-natwest-group/tech-data-and-AI/natwest-ai-adoption-report/how-we-use-AI-for-the-future-of-customer-relationships.html",
    "https://www.natwestgroup.com/news-and-insights/latest-stories/ai-and-data/2026/feb/being-a-trusted-partner-for-tomorrows-banking-through-technology.html",
]
settings = Settings(
    seed_urls=urls, delay_seconds=2, retries=1, request_timeout=25, max_runtime_seconds=500
)
fetcher = SnapshotFetcher(settings, Path("output/research-more"))
try:
    for url in urls:
        try:
            final, _ = fetcher.fetch(url)
            print(json.dumps({"url": final, "status": "fetched"}), flush=True)
        except (FetchError, ValueError, OSError) as exc:
            print(json.dumps({"url": url, "reason": str(exc)}), flush=True)
finally:
    fetcher.close()
