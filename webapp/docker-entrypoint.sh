#!/bin/sh
set -e

case "$1" in
    web)
        exec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 wsgi:app
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
