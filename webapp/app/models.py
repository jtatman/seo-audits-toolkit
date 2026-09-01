from datetime import datetime, timezone

from flask_login import UserMixin
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
