from flask import Flask

from .extensions import csrf, db, login_manager


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401 - registers models with SQLAlchemy

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from .auth import bp as auth_bp
    from .extractor import bp as extractor_bp
    from .keywords import bp as keywords_bp
    from .sites import bp as sites_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(keywords_bp)
    app.register_blueprint(extractor_bp)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/healthz/jobs")
    def healthz_jobs():
        from .jobs import ping

        result = ping()
        try:
            value = result(blocking=True, timeout=5)
        except Exception as exc:  # huey.exceptions.TaskException on worker error
            return {"status": "error", "detail": str(exc)}, 500
        return {"status": "ok", "result": value}

    with app.app_context():
        db.create_all()

    return app
