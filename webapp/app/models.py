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
    """params: {start_url, max_pages, run_keywords, run_summaries, summarize_top_n}.

    v0.2: replaces the old fused single-task crawl (one function call per
    page doing fetch+keywords+AI-SEO together) with a phase-separated
    pipeline - see jobs.py's run_discovery/run_content_download/
    run_ai_seo_checks/run_keyword_extraction/run_summarization, each its
    own Huey task, auto-chained. `result` (inherited from ScanMixin) is
    unused here - per-page state lives on CrawledPage rows instead of one
    JSON blob assembled at the end, which is what makes incremental
    progress and per-page detail pages possible. Keyword extraction and
    summarization are opt-in (run_keywords/run_summaries) - discovery +
    download + AI-SEO checks + the link graph are the always-on baseline
    "survey the site" behavior; the expensive ML-driven phases are extra.

    Keyword extraction uses KeyBERT, not yake - yake has a documented
    O(k^2) pairwise-Levenshtein deduplication step (github.com/LIAAD/yake
    issue #80) that hung a real crawl for 2h40+ minutes on an unusually
    large page. KeyBERT's cost scales with candidate count, not pairwise
    comparisons, and reuses the transformers/torch dependency already
    accepted for the bert summarizer.
    """

    phase = db.Column(db.String(30), default="discovering", nullable=False)
    # discovering -> downloading -> checking_ai_seo
    #   -> [extracting_keywords if run_keywords] -> [summarizing if run_summaries] -> done
    discovery_method = db.Column(db.String(10), nullable=True)  # "sitemap" | "crawl"
    pages_discovered = db.Column(db.Integer, default=0, nullable=False)
    pages_downloaded = db.Column(db.Integer, default=0, nullable=False)
    pages_keyword_extracted = db.Column(db.Integer, default=0, nullable=False)
    pages_summarized = db.Column(db.Integer, default=0, nullable=False)
    site_ai_seo = db.Column(db.JSON, nullable=True)
    bokeh_item = db.Column(db.JSON, nullable=True)
    related_pages = db.Column(db.JSON, nullable=True)

    pages = db.relationship(
        "CrawledPage", back_populates="scan", cascade="all, delete-orphan"
    )


class CrawledPage(db.Model):
    """One row per page discovered by a SiteCrawlScan. Each phase's status
    lives per-page (not nested in one JSON blob) so the UI can show
    granular per-page, per-phase progress during a running crawl and give
    every page its own detail view instead of one giant scrolling table."""

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(
        db.Integer, db.ForeignKey("site_crawl_scan.id"), nullable=False
    )
    url = db.Column(db.String(2048), nullable=False)

    fetch_status = db.Column(db.String(20), default="pending", nullable=False)
    # pending/done/failed/skipped - "skipped" means the URL returned
    # non-HTML content (a PDF, image, etc.) and was deliberately not
    # parsed - see NotHtmlContentError in scrapers/crawl.py.
    fetch_error = db.Column(db.Text, nullable=True)
    internal_links = db.Column(db.JSON, nullable=True)
    ai_seo = db.Column(db.JSON, nullable=True)

    keywords_status = db.Column(db.String(20), default="not_requested", nullable=False)
    keywords = db.Column(db.JSON, nullable=True)
    keywords_error = db.Column(db.Text, nullable=True)

    summary_status = db.Column(db.String(20), default="not_requested", nullable=False)
    summary = db.Column(db.Text, nullable=True)
    summary_error = db.Column(db.Text, nullable=True)

    scan = db.relationship("SiteCrawlScan", back_populates="pages")
