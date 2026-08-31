import json
import subprocess

import pytz
import time
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone

from .models import Lighthouse, Lighthouse_Result

# Lighthouse's category set has changed over time (e.g. "pwa" was dropped
# as a default category) - use .get() rather than a bare [...] lookup so a
# category Lighthouse stops reporting doesn't crash the whole task.
# pwa_score is a non-nullable CharField, so fall back to a placeholder
# string rather than None.
def _extract_scores(result):
    categories = result["categories"]
    return {
        "performance_score": categories.get("performance", {}).get("score"),
        "accessibility_score": categories.get("accessibility", {}).get("score"),
        "best_practices_score": categories.get("best-practices", {}).get("score"),
        "seo_score": categories.get("seo", {}).get("score"),
        "pwa_score": categories.get("pwa", {}).get("score", "N/A"),
    }


## Declaration of a task to be used with celery
@shared_task
def lighthouse_crawler():
    scheduled = Lighthouse.objects.filter(scheduled=True)
    for item in scheduled:
        print(item)
        print(item.url)
        result = json.loads(run_lighthouse(item.url))
        results_db = Lighthouse_Result(org=item.org, url=item, timestamp=timezone.now(), **_extract_scores(result))
        results_db.save()
        Lighthouse.objects.filter(org=item.org,url=item.url).update(last_updated=timezone.now())
        print("Done")

## Declaration of a task to be used with celery
@shared_task()
def lighthouse_add_new_url_crawler(url):
    time.sleep(0.2)
    Lighthouse_Object = Lighthouse.objects.filter(url=url).first()
    result = json.loads(run_lighthouse(url))
    results_db = Lighthouse_Result(org=Lighthouse_Object.org, url=Lighthouse_Object, timestamp=timezone.now(), **_extract_scores(result))
    results_db.save()
    Lighthouse.objects.filter(org=Lighthouse_Object.org,url=url).update(last_updated=timezone.now())
    print("Done")


def run_lighthouse(url):
    # subprocess.run with an argument list (no shell=True) - url is
    # user-supplied and must never be interpolated into a shell command
    # string, which would let a crafted url run arbitrary shell commands.
    proc = subprocess.run(
        ["lighthouse", "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage", url, "--output", "json"],
        stdout=subprocess.PIPE,
    )
    return proc.stdout.decode("utf-8")
