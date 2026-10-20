import codecs
import logging
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .urls import in_scope, normalize_url, require_public_url

log = logging.getLogger(__name__)


class FetchError(Exception):
    pass


class Skipped(FetchError):
    pass


class BudgetExceeded(FetchError):
    pass


class Fetcher:
    def __init__(
        self,
        settings,
        *,
        deadline=None,
        session=None,
        clock=time.monotonic,
        sleeper=time.sleep,
        public_check=require_public_url,
    ):
        self.settings = settings
        self.clock, self.sleeper, self.public_check = clock, sleeper, public_check
        self.deadline = deadline if deadline is not None else clock() + settings.max_runtime_seconds
        self.session = session or requests.Session()
        self.session.trust_env = False  # Do not silently use proxy or netrc credentials.
        self.session.headers.update({"User-Agent": settings.user_agent})
        self.last_request = {}
        self.robots = {}
        self.delays = {}

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise BudgetExceeded("crawl runtime budget reached")
        return remaining

    def pause(self, seconds):
        if seconds >= self.remaining():
            raise BudgetExceeded("insufficient runtime for request delay")
        if seconds > 0:
            self.sleeper(seconds)

    def raw(self, url):
        origin = urlsplit(url).netloc
        for attempt in range(self.settings.retries + 1):
            self.public_check(url)
            delay = max(self.settings.delay_seconds, self.delays.get(origin, 0))
            self.pause(max(0, self.last_request.get(origin, -float("inf")) + delay - self.clock()))
            self.last_request[origin] = self.clock()
            timeout = min(self.settings.request_timeout, self.remaining())
            try:
                # Never carry server cookies from one page to another.
                self.session.cookies.clear()
                with self.session.get(
                    url, timeout=timeout, allow_redirects=False, stream=True
                ) as r:
                    if r.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self.settings.retries:
                            raise FetchError(f"HTTP {r.status_code}")
                        retry_after = r.headers.get("Retry-After", "")
                        try:
                            backoff = max(2**attempt, float(retry_after))
                        except ValueError:
                            backoff = 2**attempt
                        self.pause(min(backoff, 120))
                        continue
                    chunks, size = [], 0
                    for chunk in r.iter_content(chunk_size=16384):
                        self.remaining()
                        size += len(chunk)
                        if size > self.settings.max_response_bytes:
                            raise Skipped("response exceeds configured byte limit")
                        chunks.append(chunk)
                    encoding = (
                        r.encoding
                        if "charset=" in r.headers.get("Content-Type", "").lower()
                        else "utf-8"
                    )
                    try:
                        codecs.lookup(encoding or "utf-8")
                    except LookupError:
                        encoding = "utf-8"
                    return r.status_code, r.headers.copy(), b"".join(chunks), encoding or "utf-8"
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == self.settings.retries:
                    raise FetchError(type(exc).__name__) from exc
                self.pause(2**attempt)
            except requests.RequestException as exc:
                raise FetchError(type(exc).__name__) from exc
        raise FetchError("retry limit exceeded")

    def robot_allowed(self, url):
        p = urlsplit(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            # Robots redirects are conservatively blocked rather than followed unchecked.
            status, _, body, encoding = self.raw(origin + "/robots.txt")
            robot = RobotFileParser()
            if status == 404:
                robot.parse([])
            elif status == 200:
                robot.parse(body.decode(encoding, errors="replace").splitlines())
            else:
                raise Skipped(f"robots unavailable or restrictive: HTTP {status}")
            self.robots[origin] = robot
            delay = robot.crawl_delay(self.settings.user_agent) or robot.crawl_delay("*") or 0
            rate = robot.request_rate(self.settings.user_agent) or robot.request_rate("*")
            if rate and rate.requests:
                delay = max(delay, rate.seconds / rate.requests)
            self.delays[p.netloc] = delay
        return self.robots[origin].can_fetch(self.settings.user_agent, url)

    def fetch(self, url):
        visited = set()
        for _ in range(6):
            if url in visited:
                raise FetchError("redirect loop")
            visited.add(url)
            if not in_scope(url, self.settings):
                raise Skipped("URL outside configured scope")
            if not self.robot_allowed(url):
                raise Skipped("robots.txt disallows URL")
            status, headers, body, encoding = self.raw(url)
            if status in {301, 302, 303, 307, 308}:
                destination = normalize_url(urljoin(url, headers.get("Location", "")))
                if not destination:
                    raise Skipped("invalid redirect")
                url = destination
                continue
            if status != 200:
                raise FetchError(f"HTTP {status}")
            if headers.get("Content-Type", "").split(";", 1)[0].lower() not in {
                "text/html",
                "application/xhtml+xml",
            }:
                raise Skipped("unsupported content type")
            return url, body.decode(encoding, errors="replace")
        raise FetchError("too many redirects")

    def close(self):
        self.session.close()
