import json
import subprocess
import urllib.parse

import pytz
import time
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone

from .models import Security, Security_Result

## Declaration of a task to be used with celery
@shared_task
def security_crawler():
    scheduled = Security.objects.filter(scheduled=True)
    for item in scheduled:
        print(item)
        print(item.url)
        result = json.loads(run_security(item.url))
        score = result["score"]
        results_db = Security_Result(org=item.org,url=item,score=score,result=result, timestamp=timezone.now())
        results_db.save()
        Security.objects.filter(org=item.org,url=item.url).update(last_updated=timezone.now())
        print("Done")

## Declaration of a task to be used with celery
@shared_task()
def security_add_new_url_crawler(url):
    time.sleep(0.2)
    Security_Object = Security.objects.filter(url=url).first()
    result = json.loads(run_security(url))
    score = result["score"]
    results_db = Security_Result(org=Security_Object.org,url=Security_Object,result=result, score=score, timestamp=timezone.now())
    results_db.save()
    Security.objects.filter(org=Security_Object.org,url=url).update(score=score,last_updated=timezone.now())
    print("Done")


def run_security(url):
    # httpobs-cli called Mozilla's original HTTP Observatory API, shut down
    # 2024-10-31. Replaced with @mdn/mdn-http-observatory's self-hosted CLI -
    # actively maintained, runs entirely locally, no third-party API call
    # (and therefore no more "the whole feature is down because someone
    # else's server is down" failure mode).
    #
    # subprocess.run with an argument list (no shell=True) - url is
    # user-supplied and must never be interpolated into a shell command
    # string, which would let a crafted url run arbitrary shell commands.
    hostname = urllib.parse.urlparse(url).netloc or url
    proc = subprocess.run(["mdn-http-observatory-scan", hostname], stdout=subprocess.PIPE)
    result = json.loads(proc.stdout.decode("utf-8"))

    if result["scan"]["error"]:
        raise RuntimeError(f"mdn-http-observatory-scan failed for {hostname}: {result['scan']['error']}")

    computed = {}
    computed["score"] = result["scan"]["score"]
    computed["grade"] = result["scan"]["grade"]
    computed["status_code"] = result["scan"]["statusCode"]
    computed["tests_failed"] = result["scan"]["testsFailed"]
    computed["tests_passed"] = result["scan"]["testsPassed"]
    computed["tests_quantity"] = result["scan"]["testsQuantity"]

    response_headers = []
    for name, value in result["scan"]["responseHeaders"].items():
        response_headers.append({"name": name, "value": value})
    computed["response_headers"] = response_headers

    tests = []
    for name, test in result["tests"].items():
        tests.append({
            "name": name,
            "pass": test["pass"],
            "result": test["result"],
            "expectation": test["expectation"],
            # the new tool reports a numeric score impact rather than the
            # old tool's text description - fold both into one string so
            # the frontend's existing score_description field keeps working
            "score_description": f"{test['result']} ({test['scoreModifier']:+d})",
        })
    computed["tests"] = tests
    return json.dumps(computed)
