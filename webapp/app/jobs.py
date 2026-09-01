import os

from huey import SqliteHuey

huey = SqliteHuey(
    "osat", filename=os.environ.get("HUEY_DB_PATH", "/data/huey.db")
)


@huey.task()
def ping():
    """Trivial round-trip job proving web -> queue -> worker wiring works."""
    return "pong"
