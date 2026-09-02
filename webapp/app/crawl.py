from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_remaining_summaries, run_site_crawl
from .models import SiteCrawlScan
from .utils import get_owned_site_or_404

bp = Blueprint("crawl", __name__, url_prefix="/sites/<int:site_id>/crawl")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        start_url = request.form.get("start_url", "").strip()
        if not start_url:
            flash("A starting URL is required.", "error")
            return redirect(url_for("crawl.index", site_id=site.id))

        try:
            max_pages = int(request.form.get("max_pages") or 50)
        except ValueError:
            max_pages = 50

        scan = SiteCrawlScan(
            site_id=site.id,
            params={
                "start_url": start_url,
                "max_pages": max_pages,
                "summarize_top_n": 10,
            },
            status="queued",
        )
        db.session.add(scan)
        db.session.commit()

        run_site_crawl(scan.id)

        return redirect(url_for("crawl.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        SiteCrawlScan.query.filter_by(site_id=site.id)
        .order_by(SiteCrawlScan.created_at.desc())
        .all()
    )
    return render_template("crawl/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(SiteCrawlScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("crawl/detail.html", site=site, scan=scan)


@bp.post("/<int:scan_id>/summarize-remaining")
@login_required
def summarize_remaining(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(SiteCrawlScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)

    run_remaining_summaries(scan.id)
    flash("Summarizing remaining pages in the background - refresh to see progress.", "success")
    return redirect(url_for("crawl.detail", site_id=site.id, scan_id=scan.id))
