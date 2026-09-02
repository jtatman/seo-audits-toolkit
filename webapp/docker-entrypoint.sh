#!/bin/sh
set -e

case "$1" in
    web)
        # --preload imports the app (and runs db.create_all()) once in the
        # master process before forking workers - without it, each worker
        # calls create_all() independently and races on CREATE TABLE
        # against the same SQLite file.
        exec gunicorn --preload --bind 0.0.0.0:5000 --workers 2 --threads 4 wsgi:app
        ;;
    worker)
        exec huey_consumer app.jobs.huey
        ;;
    shell)
        exec python
        ;;
    *)
        exec "$@"
        ;;
esac
