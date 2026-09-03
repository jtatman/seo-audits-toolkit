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
        # -w 4: a deep security scan (wapiti) can run for several minutes:
        # with the default single worker thread it would block every other
        # queued job (keyword extraction, extractor, etc.) for the whole
        # scan. SQLite's single-writer model still serializes the actual
        # commits, but the crawling/CPU work itself now runs concurrently.
        #
        # OMP_NUM_THREADS etc: without these, KeyBERT/sentence-transformers
        # (native BLAS/torch code) segfaulted this process outright when
        # running inside huey's multi-threaded worker model - reproduced
        # directly, fixed directly. This is the standard, well-documented
        # mitigation for PyTorch-under-a-threaded-server crashes: force
        # single-threaded BLAS so its internal thread pool can't conflict
        # with the threads huey itself is running.
        export OMP_NUM_THREADS=1
        export MKL_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        export TOKENIZERS_PARALLELISM=false
        exec huey_consumer app.jobs.huey -w 4
        ;;
    shell)
        exec python
        ;;
    *)
        exec "$@"
        ;;
esac
