from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_keyword_scan
from .models import KeywordScan
from .utils import get_owned_site_or_404

bp = Blueprint("keywords", __name__, url_prefix="/sites/<int:site_id>/keywords")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            flash("Paste some text to extract keywords from.", "error")
            return redirect(url_for("keywords.index", site_id=site.id))

        params = {
            "text": text,
            "language": request.form.get("language", "en").strip() or "en",
            "ngram": int(request.form.get("ngram") or 2),
            "number_keywords": int(request.form.get("number_keywords") or 20),
        }
        scan = KeywordScan(site_id=site.id, params=params, status="queued")
        db.session.add(scan)
        db.session.commit()

        run_keyword_scan(scan.id)

        return redirect(url_for("keywords.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        KeywordScan.query.filter_by(site_id=site.id)
        .order_by(KeywordScan.created_at.desc())
        .all()
    )
    return render_template("keywords/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(KeywordScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("keywords/detail.html", site=site, scan=scan)
