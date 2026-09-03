from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_discovery, run_remaining_summaries
from .models import CrawledPage, SiteCrawlScan
from .utils import get_owned_site_or_404

bp = Blueprint("crawl", __name__, url_prefix="/sites/<int:site_id>/crawl")

PAGES_PER_PAGE = 25


def _get_scan_or_404(site, scan_id):
    scan = db.session.get(SiteCrawlScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return scan


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
        try:
            summarize_top_n = int(request.form.get("summarize_top_n") or 10)
        except ValueError:
            summarize_top_n = 10

        scan = SiteCrawlScan(
            site_id=site.id,
            params={
                "start_url": start_url,
                "max_pages": max_pages,
                "run_keywords": bool(request.form.get("run_keywords")),
                "run_summaries": bool(request.form.get("run_summaries")),
                "summarize_top_n": summarize_top_n,
            },
            status="queued",
        )
        db.session.add(scan)
        db.session.commit()

        run_discovery(scan.id)

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
    scan = _get_scan_or_404(site, scan_id)
    return render_template("crawl/detail.html", site=site, scan=scan)


@bp.get("/<int:scan_id>/pages")
@login_required
def pages(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)
    page_num = request.args.get("page", 1, type=int)
    pagination = (
        CrawledPage.query.filter_by(scan_id=scan.id)
        .order_by(CrawledPage.id)
        .paginate(page=page_num, per_page=PAGES_PER_PAGE, error_out=False)
    )
    return render_template(
        "crawl/pages.html", site=site, scan=scan, pagination=pagination
    )


@bp.get("/<int:scan_id>/pages/<int:page_id>")
@login_required
def page_detail(site_id, scan_id, page_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)
    page = db.session.get(CrawledPage, page_id)
    if page is None or page.scan_id != scan.id:
        abort(404)
    return render_template("crawl/page_detail.html", site=site, scan=scan, page=page)


@bp.get("/<int:scan_id>/graph")
@login_required
def graph(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)
    return render_template("crawl/graph.html", site=site, scan=scan)


@bp.get("/<int:scan_id>/related")
@login_required
def related(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)
    return render_template("crawl/related.html", site=site, scan=scan)


@bp.get("/<int:scan_id>/ai-seo")
@login_required
def ai_seo_overview(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)

    pages_with = {
        "schema": sum(1 for p in scan.pages if p.ai_seo and p.ai_seo.get("schema_types")),
        "byline": sum(1 for p in scan.pages if p.ai_seo and p.ai_seo.get("has_byline")),
        "freshness": sum(1 for p in scan.pages if p.ai_seo and p.ai_seo.get("freshness")),
        "faq_format": sum(1 for p in scan.pages if p.ai_seo and p.ai_seo.get("faq_format")),
    }
    pages_checked = sum(1 for p in scan.pages if p.ai_seo)

    return render_template(
        "crawl/ai_seo.html",
        site=site,
        scan=scan,
        pages_with=pages_with,
        pages_checked=pages_checked,
    )


@bp.post("/<int:scan_id>/summarize-remaining")
@login_required
def summarize_remaining(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = _get_scan_or_404(site, scan_id)

    run_remaining_summaries(scan.id)
    flash("Summarizing remaining pages in the background - refresh to see progress.", "success")
    return redirect(url_for("crawl.detail", site_id=site.id, scan_id=scan.id))
