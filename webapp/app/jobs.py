import os
from datetime import datetime, timezone

from huey import SqliteHuey

huey = SqliteHuey(
    "osat", filename=os.environ.get("HUEY_DB_PATH", "/data/huey.db")
)

_app = None


def _get_app():
    """Lazily build a Flask app instance for this worker process, so tasks
    can use `db.session` the same way request handlers do."""
    global _app
    if _app is None:
        from . import create_app

        _app = create_app()
    return _app


def _run_scan(model, scan_id, work):
    """Shared queued -> running -> finished/failed state machine for every
    Scan model. `work(params)` does the feature-specific part and returns
    the JSON-serializable result dict."""
    from .extensions import db

    app = _get_app()
    with app.app_context():
        scan = db.session.get(model, scan_id)
        if scan is None:
            return

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            scan.result = work(scan.params)
            scan.status = "finished"
        except Exception as exc:
            scan.status = "failed"
            scan.error = str(exc)
        finally:
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()


@huey.task()
def ping():
    """Trivial round-trip job proving web -> queue -> worker wiring works."""
    return "pong"


@huey.task()
def run_extractor_scan(scan_id):
    from .models import ExtractorScan
    from .scrapers.headers import find_all_headers
    from .scrapers.images import find_all_images
    from .scrapers.links import find_all_links

    scrapers = {
        "HEADERS": find_all_headers,
        "IMAGES": find_all_images,
        "LINKS": find_all_links,
    }

    def work(params):
        scraper = scrapers[params["extractor_type"]]
        return scraper(params["url"])

    _run_scan(ExtractorScan, scan_id, work)


@huey.task()
def run_pagespeed_scan(scan_id):
    from flask import current_app

    from .models import PageSpeedScan
    from .scrapers.pagespeed import run_pagespeed

    def work(params):
        return run_pagespeed(
            params["url"],
            api_key=current_app.config.get("PSI_API_KEY"),
            strategy=params.get("strategy", "mobile"),
        )

    _run_scan(PageSpeedScan, scan_id, work)


@huey.task()
def run_security_scan(scan_id):
    from .models import SecurityScan
    from .scrapers import security as security_scraper

    def work(params):
        result = {"headers": security_scraper.scan(params["url"])}
        if params.get("deep_scan"):
            from .scrapers import wapiti_scan

            result["wapiti"] = wapiti_scan.scan(params["url"])
        return result

    _run_scan(SecurityScan, scan_id, work)


# --- Site crawl: v0.2 phase-separated pipeline -----------------------------
#
# Each phase is its own task, auto-chained by calling the next task
# function at the end of the previous one's body (huey tasks are plain
# callables that enqueue themselves when called - the same mechanism
# app/crawl.py's routes already use). This replaces v1's single fused
# run_site_crawl task, whose one-function-per-page design let a single
# page's keyword extraction hang the entire pipeline for hours with no
# way for other work to proceed or for progress to be visible. See
# ~/.claude/plans/async-cooking-globe.md for the full design rationale.


@huey.task()
def run_discovery(scan_id):
    """Phase 1: find the site's pages (sitemap.xml, falling back to a
    same-domain link crawl). Creates CrawledPage rows as pages are found,
    committing incrementally so the pages list is live during a running
    crawl, not just after it finishes."""
    from .extensions import db
    from .models import CrawledPage, SiteCrawlScan
    from .scrapers import ai_seo
    from .scrapers.crawl import discover_sitemap_urls, link_crawl_discover

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return
        if scan.pages:
            # Already discovered (this task was re-invoked, e.g. after a
            # worker crash) - re-running would create duplicate CrawledPage
            # rows for the same URLs. Just resume the pipeline from here.
            run_content_download(scan_id)
            return

        scan.status = "running"
        scan.phase = "discovering"
        scan.started_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            start_url = scan.params["start_url"]
            max_pages = scan.params.get("max_pages", 50)

            sitemap_urls = discover_sitemap_urls(start_url, max_pages)
            if sitemap_urls:
                scan.discovery_method = "sitemap"
                for url in sitemap_urls:
                    db.session.add(CrawledPage(scan_id=scan.id, url=url))
                    scan.pages_discovered += 1
                db.session.commit()
            else:
                scan.discovery_method = "crawl"
                db.session.commit()

                def on_page(url, internal_links, signals, error):
                    from .scrapers.crawl import NotHtmlContentError

                    page = CrawledPage(scan_id=scan.id, url=url)
                    if isinstance(error, NotHtmlContentError):
                        # A PDF or other non-HTML resource, not a fetch
                        # failure - not analyzed, but not "broken" either.
                        page.fetch_status = "skipped"
                        page.fetch_error = str(error)
                    elif error:
                        page.fetch_status = "failed"
                        page.fetch_error = str(error)
                    else:
                        page.fetch_status = "done"
                        page.internal_links = internal_links
                        page.ai_seo = signals
                        scan.pages_downloaded += 1
                    db.session.add(page)
                    scan.pages_discovered += 1
                    db.session.commit()

                link_crawl_discover(start_url, max_pages, on_page)

            scan.site_ai_seo = {
                "robots_txt": ai_seo.check_robots_txt(start_url),
                "llms_txt_present": ai_seo.check_llms_txt(start_url),
            }
            scan.phase = "downloading"
            db.session.commit()
        except Exception as exc:
            scan.status = "failed"
            scan.error = str(exc)
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()
            return

    run_content_download(scan_id)


@huey.task()
def run_content_download(scan_id):
    """Phase 2: for pages discovered via sitemap (not yet fetched), fetch
    them in parallel and derive links + AI-SEO signals. Pages discovered
    via a link crawl are already fetched (that phase needs each page's
    links to keep going, so the work is already done) - this phase then
    just builds the link graph from what's known."""
    from urllib.parse import urlparse

    from .extensions import db
    from .models import SiteCrawlScan
    from .scrapers.crawl import build_graph, download_many, render_graph

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return

        scan.phase = "downloading"
        db.session.commit()

        try:
            domain = urlparse(scan.params["start_url"]).netloc
            pending = {p.url: p for p in scan.pages if p.fetch_status == "pending"}

            if pending:

                def on_page(url, internal_links, signals, error):
                    from .scrapers.crawl import NotHtmlContentError

                    page = pending[url]
                    if isinstance(error, NotHtmlContentError):
                        page.fetch_status = "skipped"
                        page.fetch_error = str(error)
                    elif error:
                        page.fetch_status = "failed"
                        page.fetch_error = str(error)
                    else:
                        page.fetch_status = "done"
                        page.internal_links = internal_links
                        page.ai_seo = signals
                        scan.pages_downloaded += 1
                    db.session.commit()

                download_many(list(pending.keys()), domain, on_page)

            graph_pages = {
                p.url: (p.internal_links or [])
                for p in scan.pages
                if p.fetch_status == "done"
            }
            if not graph_pages:
                raise RuntimeError("No pages could be downloaded successfully.")

            graph = build_graph(graph_pages)
            scan.bokeh_item = render_graph(graph)
            db.session.commit()
        except Exception as exc:
            scan.status = "failed"
            scan.error = str(exc)
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()
            return

    _advance_after_download(scan_id)


def _advance_after_download(scan_id):
    from .extensions import db
    from .models import SiteCrawlScan

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return
        if scan.params.get("run_keywords"):
            scan.phase = "extracting_keywords"
            db.session.commit()
            run_keyword_extraction(scan_id)
        elif scan.params.get("run_summaries"):
            scan.phase = "summarizing"
            db.session.commit()
            run_summarization(scan_id)
        else:
            scan.phase = "done"
            scan.status = "finished"
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()


@huey.task()
def run_keyword_extraction(scan_id):
    """Phase 3 (opt-in): KeyBERT keyword extraction, sequential per page
    within this task (embedding models aren't safely called concurrently
    from multiple threads on one instance) but isolated as its own task so
    it can't block download/AI-SEO progress the way v1's fused design did.
    Wrapped in a hard per-page timeout - KeyBERT doesn't have yake's O(k^2)
    blowup, but a genuinely huge page can still take real time (measured
    ~59s on a large synthetic page), and a timeout here means "stop
    waiting and move to the next page," not "prevent every possible
    slowdown"."""
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FutureTimeoutError

    from .extensions import db
    from .models import SiteCrawlScan
    from .scrapers.crawl import (
        PER_PAGE_TIMEOUT,
        compute_related_pages,
        extract_page_keywords,
    )

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return

        scan.phase = "extracting_keywords"
        db.session.commit()

        # Only pages not already successfully processed - this task can be
        # re-invoked after a crash (see docstring below on why one is
        # possible), and re-running it from scratch on every page would
        # both waste work and double-count scan.pages_keyword_extracted for
        # pages that already succeeded in an earlier, interrupted run.
        pages = [
            p
            for p in scan.pages
            if p.fetch_status == "done" and p.keywords_status != "done"
        ]
        for page in pages:
            page.keywords_status = "running"
            db.session.commit()
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(extract_page_keywords, page.url)
                    page.keywords = future.result(timeout=PER_PAGE_TIMEOUT)
                page.keywords_status = "done"
            except FutureTimeoutError:
                page.keywords_status = "failed"
                page.keywords_error = f"Timed out after {PER_PAGE_TIMEOUT}s"
            except Exception as exc:
                page.keywords_status = "failed"
                page.keywords_error = str(exc)
            # Recomputed from the real per-page state each time rather than
            # incremented, so a re-run after a crash can't drift out of
            # sync with what's actually in the database.
            scan.pages_keyword_extracted = sum(
                1 for p in scan.pages if p.keywords_status == "done"
            )
            db.session.commit()

        all_keywords = {p.url: p.keywords for p in scan.pages if p.keywords}
        scan.related_pages = compute_related_pages(all_keywords)
        db.session.commit()

    _advance_after_keywords(scan_id)


def _advance_after_keywords(scan_id):
    from .extensions import db
    from .models import SiteCrawlScan

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return
        if scan.params.get("run_summaries"):
            scan.phase = "summarizing"
            db.session.commit()
            run_summarization(scan_id)
        else:
            scan.phase = "done"
            scan.status = "finished"
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()


@huey.task()
def run_summarization(scan_id):
    """Phase 4 (opt-in): summarizes only the top `summarize_top_n` pages by
    link-degree - unconditionally summarizing every page is too slow
    (~55s/page on CPU) for anything but a small site. Not run on a
    separate Huey queue/consumer process - true isolation needs a second
    supervised process inside the worker container (or a 3rd container),
    not proportionate for a single-user self-hosted app; the -w 4 thread
    pool in docker-entrypoint.sh means this only occupies one of four
    worker slots while it runs, so it can't block the other phases/scans
    the way v1's fused design could."""
    from .extensions import db
    from .models import SiteCrawlScan
    from .scrapers.crawl import build_graph, summarize_page

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None:
            return

        scan.phase = "summarizing"
        db.session.commit()

        pages = [p for p in scan.pages if p.fetch_status == "done"]
        graph_pages = {p.url: (p.internal_links or []) for p in pages}
        graph = build_graph(graph_pages)
        degrees = dict(graph.degree())
        ranked = sorted(pages, key=lambda p: degrees.get(p.url, 0), reverse=True)

        # Skip pages already summarized in an earlier, interrupted run of
        # this same task (see run_keyword_extraction's docstring on why
        # re-invocation after a crash is a real scenario, not hypothetical).
        top_n = scan.params.get("summarize_top_n", 10)
        to_summarize = [p for p in ranked if p.summary_status != "done"][:top_n]
        for page in to_summarize:
            page.summary_status = "running"
            db.session.commit()
            try:
                page.summary = summarize_page(page.url)
                page.summary_status = "done"
            except Exception as exc:
                page.summary_status = "failed"
                page.summary_error = str(exc)
            scan.pages_summarized = sum(
                1 for p in scan.pages if p.summary_status == "done"
            )
            db.session.commit()

        scan.phase = "done"
        scan.status = "finished"
        scan.finished_at = datetime.now(timezone.utc)
        db.session.commit()


@huey.task()
def run_remaining_summaries(scan_id):
    """Follow-up action: summarizes any pages that didn't make the initial
    top-N cut. Commits after each page (not batched at the end) so
    progress is visible on refresh during what can be a many-minute job."""
    from .extensions import db
    from .models import SiteCrawlScan
    from .scrapers.crawl import summarize_page

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None or scan.status != "finished":
            return

        pending = [
            p
            for p in scan.pages
            if p.fetch_status == "done" and p.summary_status == "not_requested"
        ]

        for page in pending:
            page.summary_status = "running"
            db.session.commit()
            try:
                page.summary = summarize_page(page.url)
                page.summary_status = "done"
                scan.pages_summarized = sum(
                    1 for p in scan.pages if p.summary_status == "done"
                )
            except Exception as exc:
                page.summary_status = "failed"
                page.summary_error = str(exc)
            db.session.commit()
