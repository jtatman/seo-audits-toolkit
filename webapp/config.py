import os


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]

    # SQLite by default (single file in the shared /data volume) - no
    # Postgres container required for normal self-hosted use. Set
    # DATABASE_URL to a postgresql:// connection string to scale up.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:////data/osat.db"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Kept separate from the app DB file so web-request DB access and
    # job-queue polling don't contend for the same SQLite file's write lock.
    HUEY_DB_PATH = os.environ.get("HUEY_DB_PATH", "/data/huey.db")

    PSI_API_KEY = os.environ.get("PSI_API_KEY", "")
