from .http_tools import request_parse


def find_all_headers(url):
    soup = request_parse(url, raise_errors=True)

    result = {}
    for level in range(1, 7):
        tag = f"h{level}"
        result[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
    return result
