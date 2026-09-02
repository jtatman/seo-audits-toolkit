from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_pagespeed_scan
from .models import PageSpeedScan
from .utils import get_owned_site_or_404

bp = Blueprint("pagespeed", __name__, url_prefix="/sites/<int:site_id>/pagespeed")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        strategy = request.form.get("strategy", "mobile")
        if not url or strategy not in ("mobile", "desktop"):
            flash("A URL and a valid strategy are required.", "error")
            return redirect(url_for("pagespeed.index", site_id=site.id))

        scan = PageSpeedScan(
            site_id=site.id, params={"url": url, "strategy": strategy}, status="queued"
        )
        db.session.add(scan)
        db.session.commit()

        run_pagespeed_scan(scan.id)

        return redirect(url_for("pagespeed.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        PageSpeedScan.query.filter_by(site_id=site.id)
        .order_by(PageSpeedScan.created_at.desc())
        .all()
    )
    return render_template("pagespeed/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(PageSpeedScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("pagespeed/detail.html", site=site, scan=scan)
