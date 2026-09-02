"""AI-search-visibility ("AI-SEO" / "GEO") checks.

Grounded in an actual research pass rather than SEO-industry folklore. The
only peer-reviewed source in this space is "GEO: Generative Engine
Optimization" (Aggarwal, Murahari, et al., KDD 2024,
https://dl.acm.org/doi/10.1145/3637528.3671900) - it measured that citing
sources, adding quotations, and adding statistics each produced a 30-40%
lift in AI-answer citation visibility. Every other commonly-repeated claim
in this space (FAQ-schema multipliers, E-E-A-T citation-rate stats,
freshness-window numbers) comes from SEO-agency marketing blogs with no
disclosed methodology.

Every check below returns a plain fact plus one of these two labels -
never a fabricated composite score:
"""

import json
import re
from urllib.parse import urljoin, urlparse

import requests

from .http_tools import HEADERS

MEASURED = (
    "Measured: Princeton/Georgia Tech GEO study (KDD 2024) found this "
    "correlates with a 30-40% lift in AI-answer citation rate."
)
UNVERIFIED = (
    "Commonly recommended by SEO practitioners; effect on AI-search "
    "visibility has not been independently measured."
)

# Real, current user-agent strings for crawlers operated by AI companies.
# Training crawlers vs. search/retrieval crawlers matter differently (a
# site can reasonably want to opt out of training while still wanting to
# be cited in answers) - both are reported, distinguished by the caller.
AI_BOTS = {
    "GPTBot": "training",
    "ClaudeBot": "training",
    "CCBot": "training",
    "Amazonbot": "training",
    "meta-externalagent": "training",
    "Bytespider": "training",
    "Google-Extended": "training-opt-out",
    "Applebot-Extended": "training-opt-out",
    "OAI-SearchBot": "search",
    "Claude-SearchBot": "search",
    "PerplexityBot": "search",
    "DuckAssistBot": "search",
    "Applebot": "search",
}


def _base_url(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def check_robots_txt(url):
    """Returns {bot_name: {"allowed": bool, "kind": str}} plus a confidence
    note. A bot with no matching Disallow rule is allowed by default."""
    base = _base_url(url)
    try:
        resp = requests.get(f"{base}/robots.txt", timeout=10, headers=HEADERS)
        text = resp.text if resp.status_code == 200 else ""
    except requests.RequestException:
        text = ""

    # Minimal robots.txt parser: track which User-agent block we're in,
    # collect its Disallow paths. A bot is blocked if any Disallow rule for
    # its own block (or a wildcard "*" block) matches, and no matching
    # Allow rule overrides it - good enough for a top-level "can this bot
    # reach the site at all" signal, not a full RFC 9309 implementation.
    blocks = {}
    current_agents = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if current_agents and blocks.get(current_agents[-1]) is not None:
                current_agents = []
            current_agents.append(value)
            blocks.setdefault(value, [])
        elif key == "disallow" and current_agents:
            for agent in current_agents:
                if value:
                    blocks[agent].append(value)

    def is_blocked(bot):
        rules = blocks.get(bot, blocks.get("*", []))
        return any(path == "/" for path in rules)

    return {
        bot: {"allowed": not is_blocked(bot), "kind": kind}
        for bot, kind in AI_BOTS.items()
    }


def check_llms_txt(url):
    """https://llmstxt.org/ - a proposed (not confirmed-adopted-by-any-major-
    AI-vendor) convention for a plain-text site summary aimed at LLMs."""
    base = _base_url(url)
    try:
        resp = requests.get(f"{base}/llms.txt", timeout=10, headers=HEADERS)
        present = resp.status_code == 200 and resp.text.strip().startswith("#")
    except requests.RequestException:
        present = False
    return present


_QUESTION_RE = re.compile(r"\?\s*$")
_NUMBER_RE = re.compile(r"\b\d[\d,.]*%?\b")


def check_page_signals(soup, url, response_headers=None):
    """Per-page structural signals, derived from an already-fetched soup so
    callers don't re-request the page."""
    schema_types = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if isinstance(entry, dict) and "@type" in entry:
                t = entry["@type"]
                schema_types.extend(t if isinstance(t, list) else [t])

    has_byline = bool(
        soup.find(attrs={"rel": "author"})
        or soup.find(attrs={"itemprop": "author"})
        or soup.find(class_=re.compile(r"\bauthor\b", re.I))
    )

    freshness = None
    if response_headers and response_headers.get("Last-Modified"):
        freshness = response_headers["Last-Modified"]
    else:
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            freshness = time_tag["datetime"]

    body_text = soup.get_text(" ")
    citations_count = len(_NUMBER_RE.findall(body_text))

    faq_format = any(
        _QUESTION_RE.search(h.get_text(strip=True))
        for h in soup.find_all(["h2", "h3"])
    )

    return {
        "schema_types": sorted(set(schema_types)),
        "has_byline": has_byline,
        "freshness": freshness,
        "citations_count": citations_count,
        "faq_format": faq_format,
    }
