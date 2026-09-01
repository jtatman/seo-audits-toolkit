from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("sites.list_sites"))

    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not username or not email or not password:
            flash("Username, email, and password are all required.", "error")
            return render_template("auth/register.html")

        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            flash("That username or email is already registered.", "error")
            return render_template("auth/register.html")

        # First registered user becomes an admin - there's no other user yet
        # to grant that role, and someone has to be able to manage the
        # instance.
        is_first_user = User.query.count() == 0
        user = User(username=username, email=email, is_admin=is_first_user)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("sites.list_sites"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("sites.list_sites"))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html")

        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("sites.list_sites"))

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
