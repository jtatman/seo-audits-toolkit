from urllib.parse import urljoin

from .http_tools import request_parse


def find_all_images(url):
    soup = request_parse(url, raise_errors=True)

    seen = set()
    images = []
    missing_title = 0
    missing_alt = 0
    duplicates = 0

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("src-set")
        if not src:
            continue
        full_src = urljoin(url, src)

        if full_src in seen:
            duplicates += 1
            continue
        seen.add(full_src)

        alt = img.get("alt")
        title = img.get("title")
        if not alt:
            missing_alt += 1
        if not title:
            missing_title += 1

        images.append({"src": full_src, "alt": alt, "title": title})

    return {
        "images": images,
        "summary": {
            "total": len(images),
            "missing_alt": missing_alt,
            "missing_title": missing_title,
            "duplicates": duplicates,
        },
    }
