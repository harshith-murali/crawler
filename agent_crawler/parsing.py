from dataclasses import dataclass

from bs4 import BeautifulSoup

from .models import compact
from .urls import normalize_url


@dataclass
class Page:
    url: str
    title: str
    text: str
    links: list[str]
    blocks: list[str]
    tables: list[list[dict[str, str]]]


def parse_html(html: str, url: str) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    title = compact(soup.title.get_text(" ")) if soup.title else ""
    for element in soup(["script", "style", "noscript", "template", "nav", "footer"]):
        element.decompose()
    links = list(
        dict.fromkeys(
            u for a in soup.find_all("a", href=True) if (u := normalize_url(a["href"], url))
        )
    )
    tables = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [
            compact(c.get_text(" ")).lower().replace(" ", "_")
            for c in rows[0].find_all(["th", "td"])
        ]
        data = []
        for row in rows[1:]:
            cells = [compact(c.get_text(" ")) for c in row.find_all(["td", "th"])]
            if len(cells) == len(headers) and len(set(headers)) == len(headers):
                data.append(dict(zip(headers, cells)))
        tables.append(data)
    blocks = [compact(e.get_text(" ")) for e in soup.find_all(["p", "li"])]
    return Page(url, title, compact(soup.get_text(" ")), links, blocks, tables)
