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
def run_keyword_scan(scan_id):
    import yake

    from .models import KeywordScan

    def work(params):
        extractor = yake.KeywordExtractor(
            lan=params.get("language", "en"),
            n=params.get("ngram", 2),
            top=params.get("number_keywords", 20),
            dedupLim=0.8,
            windowsSize=2,
        )
        keywords = extractor.extract_keywords(params["text"])
        # yake scores are lower-is-more-relevant; cast off numpy's float64
        # so this is plain JSON.
        return {
            "keywords": [
                {"keyword": kw, "score": float(score)} for kw, score in keywords
            ]
        }

    _run_scan(KeywordScan, scan_id, work)


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
        result = scraper(params["url"])
        if result is None:
            raise RuntimeError(f"Could not fetch {params['url']}")
        return result

    _run_scan(ExtractorScan, scan_id, work)


@huey.task()
def run_sitemap_scan(scan_id):
    from .models import SitemapScan
    from .scrapers.sitemap import extract_urls

    def work(params):
        return extract_urls(params["url"])

    _run_scan(SitemapScan, scan_id, work)


@huey.task()
def run_internal_links_scan(scan_id):
    from .models import InternalLinksScan
    from .scrapers.internal_links import generate_graph

    def work(params):
        return generate_graph(params["url"], maximum=params.get("maximum", 200))

    _run_scan(InternalLinksScan, scan_id, work)


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
def run_summary_scan(scan_id):
    """Not run on a separate Huey queue/consumer process, unlike the
    original plan's "isolate to its own queue" aspiration - that needs a
    second supervised process inside the worker container (or a 3rd
    container), which isn't proportionate for a single-user self-hosted
    app. The -w 4 thread pool (see docker-entrypoint.sh) still means one
    slow/heavy summarize job only occupies one of four worker slots,
    leaving the others free for lightweight jobs - real memory isolation
    is the piece this doesn't have."""
    from .models import SummaryScan
    from .scrapers.summarizer import summarize

    def work(params):
        return summarize(params["text"])

    _run_scan(SummaryScan, scan_id, work)


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
