from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Site, SiteMembership
from .utils import get_owned_site_or_404, slugify

bp = Blueprint("sites", __name__, url_prefix="/sites")


@bp.get("/")
@login_required
def list_sites():
    return render_template("sites/list.html", sites=current_user.sites)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create_site():
    if request.method == "POST":
        name = request.form["name"].strip()
        url = request.form["url"].strip()
        only_domain = bool(request.form.get("only_domain"))

        if not name or not url:
            flash("Name and URL are both required.", "error")
            return render_template("sites/new.html")

        slug = base_slug = slugify(name)
        suffix = 1
        while Site.query.filter_by(slug=slug).first() is not None:
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        site = Site(name=name, slug=slug, url=url, only_domain=only_domain)
        db.session.add(site)
        db.session.flush()

        db.session.add(SiteMembership(user_id=current_user.id, site_id=site.id))
        db.session.commit()

        flash(f"Added {site.name}.", "success")
        return redirect(url_for("sites.detail", site_id=site.id))

    return render_template("sites/new.html")


@bp.get("/<int:site_id>")
@login_required
def detail(site_id):
    site = get_owned_site_or_404(site_id)
    return render_template("sites/detail.html", site=site)
