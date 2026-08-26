import pytest
from bs4 import BeautifulSoup

from crawler_python.parser import HTMLParser


@pytest.fixture
def parser():
    return HTMLParser()


SAMPLE_HTML = """
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="A test page">
    <meta name="keywords" content="test, html, parser">
    <meta property="og:title" content="OG Title">
</head>
<body>
    <h1>Main Title</h1>
    <h2>Subtitle</h2>
    <p>Hello world</p>
    <a href="/page1">Page 1</a>
    <a href="https://example.com/page2">Page 2</a>
    <a href="#anchor">Anchor</a>
    <a href="mailto:test@example.com">Email</a>
    <img src="/image.png" alt="Test image" width="100" height="200">
    <img src="https://example.com/big.jpg" alt="">
    <table>
        <tr><th>Name</th><th>Value</th></tr>
        <tr><td>A</td><td>1</td></tr>
    </table>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <ol>
        <li>First</li>
        <li>Second</li>
    </ol>
</body>
</html>
"""

BROKEN_HTML = "<html><body><p>Broken<p>Still works"


def test_parse_title(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    assert result["title"] == "Test Page"


def test_parse_links(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    links = result["links"]
    assert "https://example.com/page1" in links
    assert "https://example.com/page2" in links
    assert len(links) == 2


def test_relative_to_absolute(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com/dir/page")
    assert "https://example.com/page1" in result["links"]


def test_filter_invalid_links(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    for link in result["links"]:
        assert not link.startswith("#")
        assert not link.startswith("mailto:")


def test_extract_metadata(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    assert result["metadata"]["description"] == "A test page"
    assert result["metadata"]["keywords"] == "test, html, parser"
    assert result["metadata"]["og"]["og:title"] == "OG Title"


def test_extract_images(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    images = result["images"]
    assert len(images) == 2
    assert images[0]["src"] == "https://example.com/image.png"
    assert images[0]["alt"] == "Test image"
    assert images[0]["width"] == "100"


def test_extract_headings(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    assert "Main Title" in result["headings"]["h1"]
    assert "Subtitle" in result["headings"]["h2"]


def test_extract_tables(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    assert len(result["tables"]) == 1
    assert result["tables"][0][0] == ["Name", "Value"]
    assert result["tables"][0][1] == ["A", "1"]


def test_extract_lists(parser: HTMLParser):
    result = parser.parse_html(SAMPLE_HTML, "https://example.com")
    assert len(result["lists"]) == 2
    assert result["lists"][0]["type"] == "ul"
    assert result["lists"][0]["items"] == ["Item 1", "Item 2"]
    assert result["lists"][1]["type"] == "ol"


def test_broken_html(parser: HTMLParser):
    result = parser.parse_html(BROKEN_HTML, "https://example.com")
    assert result["text"] != ""
    assert isinstance(result["links"], list)


def test_empty_html(parser: HTMLParser):
    result = parser.parse_html("", "https://example.com")
    assert result["title"] == ""
    assert result["links"] == []


def test_extract_text_with_selector(parser: HTMLParser):
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    text = parser.extract_text(soup, "p")
    assert text == "Hello world"
