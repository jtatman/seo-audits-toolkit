import bs4
import requests


def request_parse(url, timeout=5, parser="lxml"):
    """Fetch a URL and parse it with BeautifulSoup. Returns None on any
    network/parse failure - callers treat a missing page as "nothing found"
    rather than crash the whole scan over one bad response."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return bs4.BeautifulSoup(resp.content, parser)
    except (requests.RequestException, ValueError):
        return None


def request_status_code(url, timeout=5):
    """Status code for a single link, or None if the request itself failed
    (DNS error, connection refused, timeout) - distinct from a valid HTTP
    error response like 404/500, which is a real status code to report."""
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code
    except requests.RequestException:
        return None
