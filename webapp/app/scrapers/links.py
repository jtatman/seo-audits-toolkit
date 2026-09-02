from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from .http_tools import request_parse, request_status_code

MAX_LINKS_CHECKED = 200
CONCURRENCY = 20


def find_all_links(url, max_links=MAX_LINKS_CHECKED):
    soup = request_parse(url)
    if soup is None:
        return None

    unique_links = []
    seen = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin(url, href)
        if full_url not in seen:
            seen.add(full_url)
            unique_links.append(full_url)

    checked = unique_links[:max_links]
    # Sequential status checks on a page with 100+ links can take tens of
    # seconds (measured: 135 links, ~37s serial); these are independent
    # network calls, so a small thread pool gets it down to a few seconds.
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        statuses = list(pool.map(request_status_code, checked))

    by_status = {}
    for link, status in zip(checked, statuses):
        key = str(status) if status is not None else "error"
        by_status.setdefault(key, []).append(link)

    return {
        "total_links": len(unique_links),
        "checked": len(checked),
        "truncated": len(unique_links) > max_links,
        "by_status": by_status,
    }
