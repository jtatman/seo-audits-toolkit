"""Google PageSpeed Insights v5 REST API - replaces the old Django app's
local `lighthouse` CLI shell-out entirely. One response includes both
Lighthouse lab data (lighthouseResult.categories) and real-user CrUX field
data (loadingExperience.metrics), covering the "use both" ask in a single
call. Needs a Google Cloud API key (PSI_API_KEY) - the API has zero
anonymous quota, unlike most other Google APIs.

https://developers.google.com/speed/docs/insights/rest/v5/pagespeedapi/runpagespeed
"""

import requests

API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]


def run_pagespeed(url, api_key, strategy="mobile"):
    if not api_key:
        raise RuntimeError(
            "PSI_API_KEY is not set - PageSpeed Insights needs a Google Cloud "
            "API key (the API has no anonymous quota). See README.md."
        )

    params = [
        ("url", url),
        ("key", api_key),
        ("strategy", strategy),
    ] + [("category", c) for c in CATEGORIES]

    resp = requests.get(API_URL, params=params, timeout=60)
    data = resp.json()

    if resp.status_code != 200:
        message = data.get("error", {}).get("message", resp.text[:500])
        raise RuntimeError(f"PageSpeed Insights API error ({resp.status_code}): {message}")

    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    scores = {
        cat_id: round(cat["score"] * 100) if cat.get("score") is not None else None
        for cat_id, cat in categories.items()
    }

    loading_experience = data.get("loadingExperience") or data.get("originLoadingExperience")
    field_data = None
    if loading_experience and loading_experience.get("metrics"):
        field_data = {
            "overall_category": loading_experience.get("overall_category"),
            "metrics": {
                name: {
                    "percentile": metric.get("percentile"),
                    "category": metric.get("category"),
                }
                for name, metric in loading_experience["metrics"].items()
            },
        }

    return {
        "strategy": strategy,
        "scores": scores,
        "field_data": field_data,
        "final_url": lighthouse.get("finalUrl") or lighthouse.get("finalDisplayedUrl"),
        "fetch_time": lighthouse.get("fetchTime"),
    }
