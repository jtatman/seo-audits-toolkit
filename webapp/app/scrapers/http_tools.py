import bs4
import requests

# Some sites' WAF/CDN (Cloudflare, Akamai, etc.) blocks requests with no
# User-Agent or Python's default `python-requests/X.Y` one as basic bot
# protection - confirmed live against a real site (403 with no UA, 200 with
# a browser-like one). Applied to every outbound request this app makes.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}


def request_parse(url, timeout=5, parser="lxml", raise_errors=False):
    """Fetch a URL and parse it with BeautifulSoup.

    By default returns None on any network/parse failure - fine for bulk/
    tolerant fetches (e.g. crawling many pages, where one bad page just gets
    skipped). Pass raise_errors=True for a scan's primary single fetch, so
    the real reason (403, timeout, DNS failure, ...) reaches the user
    instead of a generic "could not fetch" with no explanation.
    """
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS)
        resp.raise_for_status()
        return bs4.BeautifulSoup(resp.content, parser)
    except (requests.RequestException, ValueError) as exc:
        if raise_errors:
            raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
        return None


def request_status_code(url, timeout=5):
    """Status code for a single link, or None if the request itself failed
    (DNS error, connection refused, timeout) - distinct from a valid HTTP
    error response like 404/500, which is a real status code to report."""
    try:
        resp = requests.get(url, timeout=timeout, headers=HEADERS)
        return resp.status_code
    except requests.RequestException:
        return None
