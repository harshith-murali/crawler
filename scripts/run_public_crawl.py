"""Run the production crawler and retain exact source snapshots for local evidence review."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from agent_crawler.config import load_settings
from agent_crawler.crawler import run
from agent_crawler.http import Fetcher
from agent_crawler.parsing import parse_html


class SnapshotFetcher(Fetcher):
    def __init__(self, settings, folder):
        super().__init__(settings)
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self.manifest = []

    def fetch(self, url):
        final, html = super().fetch(url)  # Same scope, robots, rate and access checks.
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        key = hashlib.sha256(final.encode()).hexdigest()[:16]
        page = parse_html(html, final)
        (self.folder / f"{key}.html").write_text(html, encoding="utf-8")
        (self.folder / f"{key}.txt").write_text(page.text, encoding="utf-8")
        self.manifest.append(
            {
                "requested_url": url,
                "source_url": final,
                "title": page.title,
                "fetched_at": datetime.now(UTC).isoformat(),
                "sha256_utf8_html": digest,
                "html_file": f"{key}.html",
                "text_file": f"{key}.txt",
            }
        )
        return final, html

    def close(self):
        (self.folder / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )
        super().close()


def main():
    settings = load_settings("config.public.json")
    fetcher = SnapshotFetcher(settings, Path("output/sources"))
    try:
        _, summary = run(settings, fetcher=fetcher)
    finally:
        fetcher.close()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
