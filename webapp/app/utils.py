import re

from flask import abort
from flask_login import current_user


def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", text) or "site"


def get_owned_site_or_404(site_id):
    """Shared by every feature blueprint - every audit record is scoped to
    a Site, and a user may only see/act on Sites they're a member of."""
    from .extensions import db
    from .models import Site

    site = db.session.get(Site, site_id)
    if site is None or current_user not in site.users:
        abort(404)
    return site
