"""Site-crawl analysis engine, split into independent phases (v0.2):
discovery, content download (+ links + AI-SEO signals, which come free
from the same fetch), keyword extraction (KeyBERT, opt-in), and
summarization (opt-in) - each run as its own Huey task in jobs.py rather
than fused into one function call per page like v1 was. That fusion is
what let one page's keyword extraction (yake, which has a documented
O(k^2) blowup - github.com/LIAAD/yake issue #80) hang the entire pipeline
for hours with no way to see it happening or for other phases to proceed
independently.

AI-SEO signal extraction is folded into the download phase rather than
given its own separate phase/task: both need the same fetched page, and
giving it a separate phase would mean fetching every page twice for no
benefit - that would be adding a fake step for appearances, which is the
opposite of what "don't obfuscate the pipeline" means. Keyword extraction
and summarization are the phases that are genuinely independent (different
resource profile, different failure mode, opt-in), so those are the ones
that get split out.
"""

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import bs4
import networkx as nx
import requests
from bokeh.embed import json_item
from bokeh.models import HoverTool, MultiLine, Scatter
from bokeh.palettes import Viridis256
from bokeh.plotting import figure, from_networkx
from bokeh.transform import linear_cmap
from usp.tree import sitemap_tree_for_homepage
from usp.web_client.requests_client import RequestsWebClient

from . import ai_seo
from .http_tools import HEADERS
from .page_text import clean_text_from_soup, extract_text

DOWNLOAD_CONCURRENCY = 10
# Network fetches are already bounded by requests' own timeout below; this
# bounds the CPU-bound per-page work (keyword extraction) that has no
# built-in timeout of its own. Measured against a real large synthetic
# page: KeyBERT took ~59s - set generously so genuinely large (not just
# pathological) pages don't get prematurely marked failed.
PER_PAGE_TIMEOUT = 90
RELATED_PAGES_MIN_OVERLAP = 0.15
RELATED_PAGES_LIMIT = 20


def normalize_url(url):
    """A homepage linked as both "https://x.com" and "https://x.com/" (or
    any path with/without a trailing slash) is the same page. Without this,
    the crawl visits it twice under two different keys, wasting a fetch and
    then reporting the two "pages" as 100% keyword-overlapping with each
    other in the related-pages output - confirmed as a real bug by testing
    against a live site before this fix."""
    parsed = urlparse(url)
    return parsed._replace(path=parsed.path.rstrip("/"), fragment="").geturl()


def _sitemap_web_client():
    # usp's own HTTP client doesn't send a browser-like User-Agent by
    # default, which the same WAF/CDN class of sites that block our other
    # requests (see http_tools.py) also blocks - pass it a session using
    # the same headers so sitemap discovery doesn't silently fail on a
    # site that actually has a working sitemap.
    session = requests.Session()
    session.headers.update(HEADERS)
    return RequestsWebClient(session=session)


def discover_sitemap_urls(start_url, max_pages):
    """Returns a sorted list of normalized same-domain URLs from
    sitemap.xml, or [] if none found / unusable - does not fetch any page
    itself, just reads the sitemap."""
    start_url = normalize_url(start_url)
    domain = urlparse(start_url).netloc
    try:
        tree = sitemap_tree_for_homepage(start_url, web_client=_sitemap_web_client())
        return sorted(
            {
                normalize_url(p.url)
                for p in tree.all_pages()
                if urlparse(p.url).netloc == domain
            }
        )[:max_pages]
    except Exception:
        return []


class NotHtmlContentError(Exception):
    """Raised when a URL doesn't actually return HTML. Discovered why this
    matters the hard way: a "page" that turned out to be a raw PDF (a
    Content-Type: application/pdf privacy-notice document, linked from a
    real site like a normal page) fed through BeautifulSoup's HTML parser
    produces 700KB+ of PDF-internal binary noise ("xref stream", "obj
    filter", ...) that looks, to a keyword extractor, like an unusually
    huge and unusually keyword-dense page - almost certainly what actually
    triggered the original yake O(k^2) hang, not just an oversized but
    otherwise normal page. Checking Content-Type before parsing avoids
    ever generating that noise in the first place, rather than trying to
    survive it after the fact (a text-length cap alone would have masked
    the symptom without fixing why the "page" looked pathological)."""


_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")


def _fetch(url):
    resp = requests.get(url, timeout=8, headers=HEADERS)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type and not any(
        content_type.startswith(t) for t in _HTML_CONTENT_TYPES
    ):
        raise NotHtmlContentError(f"{url} is {content_type}, not HTML - not analyzed")
    return resp, bs4.BeautifulSoup(resp.content, "lxml")


def fetch_and_analyze(url, domain):
    """One fetch -> (internal_links, ai_seo_signals). Does not touch
    keywords or summaries - those are separate phases with their own
    resource profile and failure modes."""
    resp, soup = _fetch(url)
    internal_links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        full_url = normalize_url(urljoin(url, href).split("#")[0])
        if urlparse(full_url).netloc == domain:
            internal_links.append(full_url)
    signals = ai_seo.check_page_signals(soup, url, resp.headers)
    return internal_links, signals


def link_crawl_discover(start_url, max_pages, on_page):
    """BFS same-domain crawl used when there's no usable sitemap. Each page
    fetch does discovery (finds new URLs to queue) and per-page analysis
    (links + AI-SEO) together, since BFS needs a page's links before it can
    keep going - unlike the sitemap path, there's no way to get a free URL
    list before fetching. `on_page(url, internal_links, signals, error)` is
    called once per page as it's processed, for incremental DB commits."""
    start_url = normalize_url(start_url)
    domain = urlparse(start_url).netloc
    queue = [start_url]
    seen = {start_url}
    processed = 0

    while queue and processed < max_pages:
        url = queue.pop(0)
        try:
            internal_links, signals = fetch_and_analyze(url, domain)
        except (requests.RequestException, NotHtmlContentError) as exc:
            if url == start_url:
                raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
            on_page(url, None, None, exc)
            continue

        processed += 1
        on_page(url, internal_links, signals, None)

        for link in internal_links:
            if link not in seen and len(seen) < max_pages:
                seen.add(link)
                queue.append(link)


def download_many(urls, domain, on_page):
    """Parallel fetch+analyze for URLs discovered via sitemap (not yet
    fetched) - ThreadPoolExecutor pattern already proven in links.py.
    `on_page` is called once per URL as its result comes back, for
    incremental commits. A per-page timeout means one pathological page
    can only delay the batch by PER_PAGE_TIMEOUT, not hang it (Python
    can't force-kill a hung thread, so that thread keeps running in the
    background even after we stop waiting on it - an accepted limitation,
    not something achievable short of a separate OS process per page)."""
    with ThreadPoolExecutor(max_workers=DOWNLOAD_CONCURRENCY) as pool:
        futures = {pool.submit(fetch_and_analyze, url, domain): url for url in urls}
        for future, url in futures.items():
            try:
                internal_links, signals = future.result(timeout=PER_PAGE_TIMEOUT)
                on_page(url, internal_links, signals, None)
            except Exception as exc:
                on_page(url, None, None, exc)


def build_graph(pages):
    """`pages`: {url: [internal_link, ...]}"""
    g = nx.Graph()
    for page, internal_links in pages.items():
        g.add_node(page)
        for link in internal_links:
            if link in pages:
                g.add_edge(page, link)
    return g


def render_graph(g):
    degrees = dict(g.degree())
    nx.set_node_attributes(g, degrees, "degree")
    max_degree = max(max(degrees.values()) if degrees else 1, 1)

    plot = figure(
        width=800,
        height=800,
        tools="pan,wheel_zoom,save,reset",
        toolbar_location="above",
        x_range=(-1.2, 1.2),
        y_range=(-1.2, 1.2),
    )
    graph_renderer = from_networkx(g, nx.spring_layout, scale=1, center=(0, 0))
    graph_renderer.node_renderer.glyph = Scatter(
        size=15, fill_color=linear_cmap("degree", Viridis256, 0, max_degree)
    )
    graph_renderer.edge_renderer.glyph = MultiLine(
        line_color="#cccccc", line_alpha=0.6
    )
    plot.renderers.append(graph_renderer)
    plot.add_tools(HoverTool(tooltips=[("page", "@index"), ("links", "@degree")]))
    return json_item(plot, "site-crawl-graph")


MAX_KEYWORD_TEXT_LENGTH = 20000


def extract_page_keywords(url):
    """One page's keywords - fetches its own text (the download phase
    doesn't retain full page text, only links/signals, to avoid holding a
    potentially large amount of text in memory for every page of a big
    crawl).

    Text is capped to MAX_KEYWORD_TEXT_LENGTH before reaching KeyBERT. This
    is the real fix for the failure mode that motivated switching away
    from yake in the first place - not the per-page timeout wrapper the
    caller also applies. Confirmed directly against the actual page that
    caused it (a 716KB legal/privacy page on a real site): a
    ThreadPoolExecutor-based timeout does NOT reliably bound this kind of
    call, because sentence-transformers' embedding step runs native BLAS/
    torch code that can hold the GIL without yielding it back - meaning
    even the *waiting* thread's own timeout can fail to fire, since it also
    needs the GIL to wake up and check. A genuine hard timeout would need a
    separate OS process (killable from outside regardless of what it's
    doing), which isn't worth a full model-reload per page for something
    this length cap already prevents. 20k characters is several thousand
    words - more than enough for SEO keyword analysis of a single page,
    and matches the same "cap the input, don't try to out-run it" approach
    the bert summarizer already uses via its tokenizer's max_length
    truncation."""
    from .keywords import extract_keywords

    text = clean_text_from_soup(_fetch(url)[1], url)
    return extract_keywords(text[:MAX_KEYWORD_TEXT_LENGTH])


def compute_related_pages(page_keywords, top_keywords=10):
    """Pairwise keyword overlap (Jaccard over each page's top keywords)
    across all keyword-extracted pages - surfaces topical relationships a
    pure link graph misses entirely (two pages can target the same
    keywords without ever linking to each other, which is exactly the
    content-cannibalization case worth flagging). `page_keywords`:
    {url: [{"keyword": str, "score": float}, ...]}."""
    keyword_sets = {
        url: {kw["keyword"].lower() for kw in keywords[:top_keywords]}
        for url, keywords in page_keywords.items()
    }
    urls = list(keyword_sets)
    pairs = []
    for i, a in enumerate(urls):
        for b in urls[i + 1 :]:
            set_a, set_b = keyword_sets[a], keyword_sets[b]
            if not set_a or not set_b:
                continue
            shared = set_a & set_b
            if not shared:
                continue
            overlap = len(shared) / len(set_a | set_b)
            if overlap >= RELATED_PAGES_MIN_OVERLAP:
                pairs.append(
                    {
                        "page_a": a,
                        "page_b": b,
                        "overlap_score": round(overlap, 3),
                        "shared_keywords": sorted(shared),
                    }
                )
    pairs.sort(key=lambda p: p["overlap_score"], reverse=True)
    return pairs[:RELATED_PAGES_LIMIT]


def summarize_page(url):
    from .summarizer import summarize

    text = extract_text(url)
    return summarize(text)["summary"]
