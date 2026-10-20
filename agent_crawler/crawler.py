import hashlib
import logging
from collections import deque
from datetime import UTC, datetime

from .extraction import extract_records
from .http import BudgetExceeded, Fetcher, FetchError, Skipped
from .models import deduplicate
from .output import write_outputs
from .parsing import parse_html
from .providers import llm_records, search_urls
from .urls import in_scope, normalize_url

log = logging.getLogger(__name__)


def run(settings, *, fetcher=None):
    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher(settings)
    stats = {
        "started_at": datetime.now(UTC).isoformat(),
        "pages_discovered": 0,
        "pages_attempted": 0,
        "pages_fetched": 0,
        "pages_failed": 0,
        "pages_skipped": 0,
        "duplicate_pages": 0,
        "records_extracted": 0,
        "candidates_extracted": 0,
        "stop_reason": "queue_exhausted",
        "errors": [],
    }
    queue, seen, fetched_urls, digests, records = deque(), set(), set(), set(), []

    def enqueue(raw_url, depth):
        url = normalize_url(raw_url)
        if (
            url
            and in_scope(url, settings)
            and url not in seen
            and len(seen) < settings.max_discovered
        ):
            seen.add(url)
            queue.append((url, depth))
            stats["pages_discovered"] += 1

    try:
        for url in settings.seed_urls:
            enqueue(url, 0)
        for url in search_urls(settings, fetcher):
            enqueue(url, 0)
        while queue and stats["pages_attempted"] < settings.max_pages:
            url, depth = queue.popleft()
            if url in fetched_urls:
                stats["duplicate_pages"] += 1
                continue
            try:
                fetcher.remaining()
                stats["pages_attempted"] += 1
                final_url, html = fetcher.fetch(url)
                stats["pages_fetched"] += 1
                if final_url in fetched_urls:
                    stats["duplicate_pages"] += 1
                    continue
                fetched_urls.add(final_url)
                page = parse_html(html, final_url)
                # Discover links even on duplicate content to preserve path-relative navigation.
                if depth < settings.max_depth:
                    for link in page.links:
                        enqueue(link, depth + 1)
                digest = hashlib.sha256(page.text.encode("utf-8")).digest()
                if digest in digests:
                    stats["duplicate_pages"] += 1
                    continue
                digests.add(digest)
                extracted = extract_records(page)
                records.extend(extracted)
                stats["candidates_extracted"] += len(extracted)
                additional = llm_records(page, settings, fetcher)
                records.extend(additional)
                stats["candidates_extracted"] += len(additional)
            except BudgetExceeded:
                stats["stop_reason"] = "runtime_limit"
                break
            except (FetchError, ValueError, OSError) as exc:
                skipped = isinstance(exc, Skipped)
                stats["pages_skipped" if skipped else "pages_failed"] += 1
                # Never log source HTML, tokens, or request objects.
                message = str(exc) if isinstance(exc, FetchError) else type(exc).__name__
                stats["errors"].append({"url": url, "reason": message, "skipped": skipped})
                log.warning("%s: %s", url, message)
        if queue and stats["stop_reason"] == "queue_exhausted":
            stats["stop_reason"] = "page_limit"
    except BudgetExceeded:
        stats["stop_reason"] = "runtime_limit"
    finally:
        if own_fetcher:
            fetcher.close()
    records = deduplicate(records)
    stats["records_extracted"] = len(records)
    stats["discovery_limit_reached"] = len(seen) >= settings.max_discovered
    stats["finished_at"] = datetime.now(UTC).isoformat()
    stats["output_file"] = settings.output_file
    write_outputs(records, stats, settings.output_file)
    return records, stats
