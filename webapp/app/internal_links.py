from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .jobs import run_internal_links_scan
from .models import InternalLinksScan
from .utils import get_owned_site_or_404

bp = Blueprint(
    "internal_links", __name__, url_prefix="/sites/<int:site_id>/internal-links"
)


@bp.route("/", methods=["GET", "POST"])
@login_required
def index(site_id):
    site = get_owned_site_or_404(site_id)

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            flash("A URL is required.", "error")
            return redirect(url_for("internal_links.index", site_id=site.id))

        try:
            maximum = int(request.form.get("maximum") or 200)
        except ValueError:
            maximum = 200

        scan = InternalLinksScan(
            site_id=site.id, params={"url": url, "maximum": maximum}, status="queued"
        )
        db.session.add(scan)
        db.session.commit()

        run_internal_links_scan(scan.id)

        return redirect(
            url_for("internal_links.detail", site_id=site.id, scan_id=scan.id)
        )

    scans = (
        InternalLinksScan.query.filter_by(site_id=site.id)
        .order_by(InternalLinksScan.created_at.desc())
        .all()
    )
    return render_template("internal_links/index.html", site=site, scans=scans)


@bp.get("/<int:scan_id>")
@login_required
def detail(site_id, scan_id):
    site = get_owned_site_or_404(site_id)
    scan = db.session.get(InternalLinksScan, scan_id)
    if scan is None or scan.site_id != site.id:
        abort(404)
    return render_template("internal_links/detail.html", site=site, scan=scan)
