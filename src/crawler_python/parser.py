import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class HTMLParser:
    def __init__(self, base_url: str = "") -> None:
        self._base_url = base_url

    async def parse_html(self, html: str, url: str) -> dict:
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            logger.warning("Ошибка парсинга %s: %s", url, e)
            return self._empty_result(url)

        return {
            "url": url,
            "title": self._extract_title(soup),
            "text": self.extract_text(soup),
            "links": self.extract_links(soup, url),
            "metadata": self.extract_metadata(soup),
            "images": self.extract_images(soup, url),
            "headings": self.extract_headings(soup),
            "tables": self.extract_tables(soup),
            "lists": self.extract_lists(soup),
        }

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links: list[str] = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(base_url, href)
            if self._is_valid_url(absolute):
                links.append(absolute)
        return links

    def extract_text(self, soup: BeautifulSoup, selector: str | None = None) -> str:
        target = soup.select_one(selector) if selector else soup.body or soup
        return target.get_text(separator=" ", strip=True) if target else ""

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        meta: dict = {}
        meta["description"] = self._meta_content(soup, "description")
        meta["keywords"] = self._meta_content(soup, "keywords")
        og = {}
        for tag in soup.find_all("meta", attrs={"property": lambda p: p and p.startswith("og:")}):
            prop = tag.get("property", "")
            content = tag.get("content", "")
            if prop and content:
                og[prop] = content
        if og:
            meta["og"] = og
        return meta

    def extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images: list[dict] = []
        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            if not src:
                continue
            images.append({
                "src": urljoin(base_url, src),
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            })
        return images

    def extract_headings(self, soup: BeautifulSoup) -> dict[str, list[str]]:
        headings: dict[str, list[str]] = {}
        for level in range(1, 7):
            tags = soup.find_all(f"h{level}")
            if tags:
                headings[f"h{level}"] = [t.get_text(strip=True) for t in tags]
        return headings

    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables: list[list[list[str]]] = []
        for table in soup.find_all("table"):
            rows: list[list[str]] = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    def extract_lists(self, soup: BeautifulSoup) -> list[dict]:
        lists: list[dict] = []
        for tag in soup.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in tag.find_all("li", recursive=False)]
            if items:
                lists.append({"type": tag.name, "items": items})
        return lists

    def _extract_title(self, soup: BeautifulSoup) -> str:
        tag = soup.find("title")
        return tag.get_text(strip=True) if tag else ""

    def _meta_content(self, soup: BeautifulSoup, name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return tag.get("content", "") if tag else ""

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except Exception:
            return False

    @staticmethod
    def _empty_result(url: str) -> dict:
        return {
            "url": url,
            "title": "",
            "text": "",
            "links": [],
            "metadata": {},
            "images": [],
            "headings": {},
            "tables": [],
            "lists": [],
        }
