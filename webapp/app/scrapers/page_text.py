"""Extracts the visible, readable text from a page - the actual on-page
copy a search engine (or a human) would read, not markup/script/style
noise. This is what feeds keyword extraction and summarization: both
analyze a site's own existing content for SEO purposes, not arbitrary
pasted text - if you wanted a generic keyword/summarizer tool disconnected
from a site, you'd reach for yake/transformers directly rather than an SEO
audit tool."""

from .http_tools import request_parse

# Tags whose contents are never real page copy. nav/header/footer/aside/form
# matter in practice, not just in theory - a real site's homepage is mostly
# navigation chrome (menus, "patient portal" links, etc), and feeding all of
# that into yake/the summarizer drowns out the actual content, confirmed by
# testing against a real hospital site's homepage.
NOISE_TAGS = (
    "script", "style", "noscript", "template", "svg",
    "nav", "header", "footer", "aside", "form",
)


def clean_text_from_soup(soup, url=""):
    """Mutates `soup` (decomposes noise tags) and returns its clean visible
    text. Callers that need other signals (links, AI-SEO checks) from the
    same page must extract those *before* calling this."""
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    # Prefer the semantic main-content container if the page has one -
    # cuts out whatever chrome isn't already covered by the tags above
    # (cookie banners, sidebars marked up without <aside>, etc).
    content = soup.find("main") or soup.find("article") or soup

    text = content.get_text(separator=" ", strip=True)
    if not text:
        raise RuntimeError(f"No readable text found on {url}")
    return text


def extract_text(url):
    soup = request_parse(url, raise_errors=True)
    return clean_text_from_soup(soup, url)
