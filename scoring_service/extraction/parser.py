from __future__ import annotations

from html.parser import HTMLParser


class PageHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "a":
            self.links.extend(value for name, value in attrs if name.casefold() == "href" and value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.text.append(data.strip())


def parse_page(page: dict) -> tuple[str, list[str]]:
    parser = PageHTMLParser()
    if page.get("html"):
        parser.feed(str(page["html"]))
    parts = [str(page.get("title") or ""), str(page.get("content") or page.get("text") or ""), " ".join(parser.text)]
    links = list(dict.fromkeys([*(str(link) for link in page.get("social_links", []) or []), *parser.links]))
    return " ".join(part for part in parts if part), links
