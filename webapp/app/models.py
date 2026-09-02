from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import declared_attr
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    memberships = db.relationship("SiteMembership", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def sites(self):
        return [m.site for m in self.memberships]


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    only_domain = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    memberships = db.relationship(
        "SiteMembership", back_populates="site", cascade="all, delete-orphan"
    )

    @property
    def users(self):
        return [m.user for m in self.memberships]


class SiteMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("site.id"), nullable=False)
    is_admin = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="memberships")
    site = db.relationship("Site", back_populates="memberships")

    __table_args__ = (db.UniqueConstraint("user_id", "site_id"),)


class ScanMixin:
    """Consistent shape shared by every audit feature: params/result as JSON
    blobs rather than per-feature columns, status tracked directly on this
    row (no separate task_id/polling table) since the params dict is passed
    straight into the job instead of being re-queried by id - avoids the
    create-row-then-task-reads-it race condition the old Django app worked
    around with a raw sleep(0.2)."""

    id = db.Column(db.Integer, primary_key=True)
    params = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), default="queued", nullable=False)
    result = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    @declared_attr
    def site_id(cls):
        return db.Column(db.Integer, db.ForeignKey("site.id"), nullable=False)

    @declared_attr
    def site(cls):
        return db.relationship("Site")


class ExtractorScan(ScanMixin, db.Model):
    """headers/images/links extraction - params: {url, extractor_type}
    where extractor_type is HEADERS/IMAGES/LINKS."""


class SecurityScan(ScanMixin, db.Model):
    """params: {url, deep_scan}. Passive header check always runs; deep_scan
    additionally runs wapiti's active vulnerability probes (result gets a
    "wapiti" key when that ran)."""


class PageSpeedScan(ScanMixin, db.Model):
    """params: {url, strategy}. strategy is "mobile" or "desktop"."""


class SiteCrawlScan(ScanMixin, db.Model):
    """params: {start_url, max_pages, summarize_top_n}.

    Replaces the old standalone KeywordScan/SummaryScan/SitemapScan/
    InternalLinksScan - this is an SEO tool, so keyword extraction and
    summarization only make sense analyzing a site's own crawled content,
    not arbitrary pasted text. One crawl discovers pages (sitemap.xml if
    present, else a same-domain link crawl), analyzes every page's own
    on-page text (keywords always - fast; a summary only for the top
    `summarize_top_n` pages by link-degree - ~55s/page on CPU, too slow to
    run unconditionally on every page of a large site), computes which
    pages relate to each other by keyword overlap (not just hyperlinks),
    and checks AI-search-visibility signals (robots.txt AI-bot access,
    llms.txt, structured data, byline, freshness, citations, FAQ format).

    result shape:
    {
      "discovery_method": "sitemap" | "crawl",
      "pages_discovered": int, "pages_analyzed": int, "pages_summarized": int,
      "site_ai_seo": {"robots_txt": {bot: allowed_bool}, "llms_txt_present": bool},
      "pages": {url: {"keywords": [...], "summary": str|null,
                       "internal_links": [...], "ai_seo": {...}}},
      "related_pages": [{"page_a", "page_b", "overlap_score", "shared_keywords"}],
      "bokeh_item": {...}
    }
    """
