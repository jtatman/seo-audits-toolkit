from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_summary_scan
from .models import SummaryScan
from .utils import get_owned_site_or_404

bp = Blueprint("summarizer", __name__, url_prefix="/sites/<int:site_id>/summarize")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            flash("Paste some text to summarize.", "error")
            return redirect(url_for("summarizer.index", site_id=site.id))

        scan = SummaryScan(site_id=site.id, params={"text": text}, status="queued")
        db.session.add(scan)
        db.session.commit()

        run_summary_scan(scan.id)

        return redirect(url_for("summarizer.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        SummaryScan.query.filter_by(site_id=site.id)
        .order_by(SummaryScan.created_at.desc())
        .all()
    )
    return render_template("summarizer/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(SummaryScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("summarizer/detail.html", site=site, scan=scan)
