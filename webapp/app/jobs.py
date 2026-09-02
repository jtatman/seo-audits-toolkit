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


@huey.task()
def ping():
    """Trivial round-trip job proving web -> queue -> worker wiring works."""
    return "pong"


@huey.task()
def run_keyword_scan(scan_id):
    import yake

    from .extensions import db
    from .models import KeywordScan

    app = _get_app()
    with app.app_context():
        scan = db.session.get(KeywordScan, scan_id)
        if scan is None:
            return

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        db.session.commit()

        try:
            params = scan.params
            extractor = yake.KeywordExtractor(
                lan=params.get("language", "en"),
                n=params.get("ngram", 2),
                top=params.get("number_keywords", 20),
                dedupLim=0.8,
                windowsSize=2,
            )
            keywords = extractor.extract_keywords(params["text"])
            # yake scores are lower-is-more-relevant; cast off numpy's
            # float64 so this is plain JSON.
            scan.result = {
                "keywords": [
                    {"keyword": kw, "score": float(score)} for kw, score in keywords
                ]
            }
            scan.status = "finished"
        except Exception as exc:
            scan.status = "failed"
            scan.error = str(exc)
        finally:
            scan.finished_at = datetime.now(timezone.utc)
            db.session.commit()
