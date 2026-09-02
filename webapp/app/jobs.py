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


@huey.task()
def run_site_crawl(scan_id):
    """Not run on a separate Huey queue/consumer process for the same
    reason the old per-page summarizer wasn't - see run_remaining_summaries
    below. The -w 4 thread pool in docker-entrypoint.sh means one slow
    crawl only occupies one of four worker slots."""
    from .models import SiteCrawlScan
    from .scrapers.crawl import run_crawl

    def work(params):
        return run_crawl(
            params["start_url"],
            params.get("max_pages", 50),
            params.get("summarize_top_n", 10),
        )

    _run_scan(SiteCrawlScan, scan_id, work)


@huey.task()
def run_remaining_summaries(scan_id):
    """Enrichment of an already-finished SiteCrawlScan, not a fresh
    queued->running->finished lifecycle - the scan stays "finished"
    throughout while this fills in summaries for pages that didn't make the
    initial top-N cut. Commits after each page (not batched at the end) so
    progress is visible on refresh during what can be a many-minute job."""
    from sqlalchemy.orm.attributes import flag_modified

    from .extensions import db
    from .models import SiteCrawlScan
    from .scrapers.page_text import extract_text
    from .scrapers.summarizer import summarize

    app = _get_app()
    with app.app_context():
        scan = db.session.get(SiteCrawlScan, scan_id)
        if scan is None or scan.status != "finished":
            return

        pending = [
            url
            for url, analysis in scan.result["pages"].items()
            if not analysis.get("summary")
        ]

        for url in pending:
            try:
                text = extract_text(url)
                scan.result["pages"][url]["summary"] = summarize(text)["summary"]
                scan.result["pages_summarized"] = (
                    scan.result.get("pages_summarized", 0) + 1
                )
            except Exception as exc:
                scan.result["pages"][url]["summary_error"] = str(exc)
            flag_modified(scan, "result")
            db.session.commit()
