from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_extractor_scan
from .models import ExtractorScan
from .utils import get_owned_site_or_404

bp = Blueprint("extractor", __name__, url_prefix="/sites/<int:site_id>")

EXTRACTOR_TYPES = ["HEADERS", "IMAGES", "LINKS"]


@bp.route("/extractor", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        extractor_type = request.form.get("extractor_type", "")
        if not url or extractor_type not in EXTRACTOR_TYPES:
            flash("A URL and a valid extraction type are both required.", "error")
            return redirect(url_for("extractor.index", site_id=site.id))

        scan = ExtractorScan(
            site_id=site.id,
            params={"url": url, "extractor_type": extractor_type},
            status="queued",
        )
        db.session.add(scan)
        db.session.commit()

        run_extractor_scan(scan.id)

        return redirect(url_for("extractor.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        ExtractorScan.query.filter_by(site_id=site.id)
        .order_by(ExtractorScan.created_at.desc())
        .all()
    )
    return render_template(
        "extractor/index.html", site=site, scans=scans, extractor_types=EXTRACTOR_TYPES
    )


@bp.get("/extractor/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(ExtractorScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("extractor/detail.html", site=site, scan=scan)
