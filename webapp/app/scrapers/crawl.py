"""Unified site-crawl analysis engine.

Discovers a site's pages (via sitemap.xml when present, falling back to a
same-domain link crawl), then derives everything about each page - internal
links, on-page-text keywords, AI-search-visibility signals - from a single
fetch per page. Replaces what used to be three separate features (sitemap
extraction, internal-link crawling, keyword extraction) each re-fetching
the same pages independently.
"""

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import bs4
import networkx as nx
import requests
import yake
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
from .summarizer import summarize

CONCURRENCY = 10


def _normalize_url(url):
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
RELATED_PAGES_MIN_OVERLAP = 0.15
RELATED_PAGES_LIMIT = 20


def _fetch(url):
    resp = requests.get(url, timeout=8, headers=HEADERS)
    resp.raise_for_status()
    return resp, bs4.BeautifulSoup(resp.content, "lxml")


def _extract_keywords(text, top=15):
    extractor = yake.KeywordExtractor(
        lan="en", n=2, top=top, dedupLim=0.8, windowsSize=2
    )
    keywords = extractor.extract_keywords(text)
    return [{"keyword": kw, "score": float(score)} for kw, score in keywords]


def _analyze_soup(url, soup, response_headers, domain):
    """Derives internal links and AI-SEO signals from the pristine soup
    first (both need tags that keyword extraction's text-cleaning step
    removes), then cleans the soup in place for keyword extraction."""
    internal_links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        full_url = _normalize_url(urljoin(url, href).split("#")[0])
        if urlparse(full_url).netloc == domain:
            internal_links.append(full_url)

    signals = ai_seo.check_page_signals(soup, url, response_headers)

    try:
        text = clean_text_from_soup(soup, url)
        keywords = _extract_keywords(text)
    except RuntimeError:
        keywords = []

    return {
        "keywords": keywords,
        "summary": None,
        "internal_links": internal_links,
        "ai_seo": signals,
    }


def analyze_page(url, domain):
    resp, soup = _fetch(url)
    return _analyze_soup(url, soup, resp.headers, domain)


def _analyze_many(urls, domain):
    """Parallel per-page analysis for the sitemap path, which already has
    the full URL list up front - same ThreadPoolExecutor pattern already
    proven in links.py for the LINKS-extraction perf fix."""
    pages = {}

    def work(url):
        try:
            return url, analyze_page(url, domain)
        except (requests.RequestException, RuntimeError):
            return url, None

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for url, analysis in pool.map(work, urls):
            if analysis is not None:
                pages[url] = analysis

    return pages


def _link_crawl(start_url, max_pages):
    """BFS same-domain crawl. Each page fetch immediately produces its full
    analysis (links to grow the queue + keywords + AI-SEO signals) - unlike
    the sitemap path, this doesn't get a free URL list before analyzing, so
    discovery and analysis happen together per page rather than as two
    passes over the same pages."""
    start_url = _normalize_url(start_url)
    domain = urlparse(start_url).netloc
    pages = {}
    queue = [start_url]
    seen = {start_url}

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        try:
            resp, soup = _fetch(url)
        except requests.RequestException as exc:
            if url == start_url:
                raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
            continue

        analysis = _analyze_soup(url, soup, resp.headers, domain)
        pages[url] = analysis

        for link in analysis["internal_links"]:
            if link not in seen and len(seen) < max_pages:
                seen.add(link)
                queue.append(link)

    return pages


def discover_and_analyze(start_url, max_pages):
    """Returns (pages: {url: analysis}, discovery_method, pages_discovered)."""
    start_url = _normalize_url(start_url)
    domain = urlparse(start_url).netloc
    try:
        tree = sitemap_tree_for_homepage(
            start_url, web_client=_sitemap_web_client()
        )
        sitemap_urls = sorted(
            {
                _normalize_url(p.url)
                for p in tree.all_pages()
                if urlparse(p.url).netloc == domain
            }
        )[:max_pages]
    except Exception:
        sitemap_urls = []

    if sitemap_urls:
        pages = _analyze_many(sitemap_urls, domain)
        if pages:
            return pages, "sitemap", len(sitemap_urls)
        # Sitemap listed URLs but every single fetch failed (e.g. the
        # sitemap is stale) - fall through to a live link crawl instead.

    pages = _link_crawl(start_url, max_pages)
    return pages, "crawl", len(pages)


def build_graph(pages):
    g = nx.Graph()
    for page, analysis in pages.items():
        g.add_node(page)
        for link in analysis["internal_links"]:
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


def compute_related_pages(pages, top_keywords=10):
    """Pairwise keyword overlap (Jaccard over each page's top keywords)
    across all analyzed pages - surfaces topical relationships a pure link
    graph misses entirely (two pages can target the same keywords without
    ever linking to each other, which is exactly the content-cannibalization
    case worth flagging)."""
    keyword_sets = {
        url: {kw["keyword"].lower() for kw in analysis["keywords"][:top_keywords]}
        for url, analysis in pages.items()
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


def summarize_top_pages(pages, graph, top_n):
    """Summarizes only the top `top_n` pages by link-degree - summarizing
    every page unconditionally is too slow (~55s/page on CPU) for anything
    but a small site. Re-fetches each page's text rather than keeping full
    text around for every analyzed page (which could be a lot of memory for
    a large crawl) - an acceptable cost since it only runs for a handful of
    pages."""
    degrees = dict(graph.degree())
    ranked = sorted(pages.keys(), key=lambda u: degrees.get(u, 0), reverse=True)

    count = 0
    for url in ranked[:top_n]:
        try:
            text = extract_text(url)
            pages[url]["summary"] = summarize(text)["summary"]
            count += 1
        except Exception as exc:
            pages[url]["summary_error"] = str(exc)
    return count


def run_crawl(start_url, max_pages, summarize_top_n):
    pages, discovery_method, pages_discovered = discover_and_analyze(
        start_url, max_pages
    )
    if not pages:
        raise RuntimeError(f"Could not discover or analyze any pages from {start_url}")

    graph = build_graph(pages)
    bokeh_item = render_graph(graph)
    related_pages = compute_related_pages(pages)
    pages_summarized = summarize_top_pages(pages, graph, summarize_top_n)

    return {
        "discovery_method": discovery_method,
        "pages_discovered": pages_discovered,
        "pages_analyzed": len(pages),
        "pages_summarized": pages_summarized,
        "site_ai_seo": {
            "robots_txt": ai_seo.check_robots_txt(start_url),
            "llms_txt_present": ai_seo.check_llms_txt(start_url),
        },
        "pages": pages,
        "related_pages": related_pages,
        "bokeh_item": bokeh_item,
    }
