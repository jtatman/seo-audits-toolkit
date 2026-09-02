from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_security_scan
from .models import SecurityScan
from .utils import get_owned_site_or_404

bp = Blueprint("security", __name__, url_prefix="/sites/<int:site_id>/security")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            flash("A URL is required.", "error")
            return redirect(url_for("security.index", site_id=site.id))

        scan = SecurityScan(
            site_id=site.id,
            params={"url": url, "deep_scan": bool(request.form.get("deep_scan"))},
            status="queued",
        )
        db.session.add(scan)
        db.session.commit()

        run_security_scan(scan.id)

        return redirect(url_for("security.detail", site_id=site.id, scan_id=scan.id))

    scans = (
        SecurityScan.query.filter_by(site_id=site.id)
        .order_by(SecurityScan.created_at.desc())
        .all()
    )
    return render_template("security/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(SecurityScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("security/detail.html", site=site, scan=scan)
