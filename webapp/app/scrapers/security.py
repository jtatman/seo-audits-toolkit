"""In-process security header check, replacing the old Django app's
dependency on the Node `mdn-http-observatory-scan` CLI. Covers the same
category of checks MDN's HTTP Observatory does (and the older Mozilla
Observatory before it) - presence/quality of the standard security-relevant
response headers - reimplemented directly so the whole app stays pure
Python with no Node runtime in the image."""

import requests

from .http_tools import HEADERS

CHECKS = [
    "content_security_policy",
    "strict_transport_security",
    "x_content_type_options",
    "x_frame_options",
    "referrer_policy",
    "permissions_policy",
    "cookies",
]


def _check_csp(headers):
    value = headers.get("Content-Security-Policy")
    if not value:
        return False, "csp-not-implemented", "Content-Security-Policy header is set"
    if "unsafe-inline" in value or "unsafe-eval" in value:
        return (
            False,
            "csp-unsafe-inline",
            "Content-Security-Policy does not allow unsafe-inline/unsafe-eval",
        )
    return True, "csp-implemented", "Content-Security-Policy header is set"


def _check_hsts(headers, is_https):
    if not is_https:
        return False, "hsts-not-applicable", "Site not served over HTTPS"
    value = headers.get("Strict-Transport-Security")
    if not value:
        return False, "hsts-not-implemented", "Strict-Transport-Security header is set"
    max_age_directive = _find_directive(value, "max-age")
    try:
        max_age = int(max_age_directive.split("=", 1)[1]) if max_age_directive else 0
    except (ValueError, IndexError):
        max_age = 0
    if max_age < 15552000:  # 180 days, matches the old Observatory's floor
        return (
            False,
            "hsts-max-age-too-short",
            "Strict-Transport-Security max-age is at least 15552000 seconds",
        )
    return True, "hsts-implemented", "Strict-Transport-Security header is set"


def _find_directive(value, name):
    for part in value.split(";"):
        part = part.strip()
        if part.startswith(name):
            return part
    return None


def _check_xcto(headers):
    value = headers.get("X-Content-Type-Options", "").lower()
    if value == "nosniff":
        return True, "xcto-nosniff", "X-Content-Type-Options header is nosniff"
    return False, "xcto-not-implemented", "X-Content-Type-Options header is nosniff"


def _check_xfo(headers):
    csp = headers.get("Content-Security-Policy", "")
    if "frame-ancestors" in csp:
        return True, "xfo-implemented-via-csp", "Clickjacking protection via frame-ancestors"
    value = headers.get("X-Frame-Options", "").upper()
    if value in ("DENY", "SAMEORIGIN"):
        return True, "xfo-implemented", "X-Frame-Options header is present"
    return False, "xfo-not-implemented", "X-Frame-Options header is present"


def _check_referrer_policy(headers):
    value = headers.get("Referrer-Policy")
    if value:
        return True, "referrer-policy-set", "Referrer-Policy header is set"
    return False, "referrer-policy-not-set", "Referrer-Policy header is set"


def _check_permissions_policy(headers):
    value = headers.get("Permissions-Policy")
    if value:
        return True, "permissions-policy-set", "Permissions-Policy header is set"
    return False, "permissions-policy-not-set", "Permissions-Policy header is set"


def _check_cookies(response):
    # response.headers collapses repeated Set-Cookie headers into one
    # (comma-joined), which breaks parsing when a site sets multiple
    # cookies - read the raw per-cookie list from urllib3 instead.
    set_cookie_headers = response.raw.headers.get_all("Set-Cookie") if response.raw else []
    if not set_cookie_headers:
        return True, "cookies-not-found", "No cookies set, or all cookies are secure"

    for raw_cookie in set_cookie_headers:
        attrs = [a.strip().lower() for a in raw_cookie.split(";")]
        if "secure" not in attrs or "httponly" not in attrs:
            return (
                False,
                "cookies-without-secure-flag",
                "All cookies use the Secure and HttpOnly flags",
            )
    return True, "cookies-secure", "All cookies use the Secure and HttpOnly flags"


def scan(url):
    response = requests.get(url, timeout=10, headers=HEADERS)
    headers = response.headers
    is_https = response.url.startswith("https://")

    checks = []

    def add(name, result):
        passed, key, expectation = result
        checks.append(
            {
                "name": name,
                "pass": passed,
                "result": key,
                "expectation": expectation,
                "score_description": ("pass" if passed else "fail") + f" ({key})",
            }
        )

    add("content-security-policy", _check_csp(headers))
    add("strict-transport-security", _check_hsts(headers, is_https))
    add("x-content-type-options", _check_xcto(headers))
    add("x-frame-options", _check_xfo(headers))
    add("referrer-policy", _check_referrer_policy(headers))
    add("permissions-policy", _check_permissions_policy(headers))
    add("cookies", _check_cookies(response))

    passed_count = sum(1 for c in checks if c["pass"])
    score = round(100 * passed_count / len(checks))
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "status_code": response.status_code,
        "tests_passed": passed_count,
        "tests_failed": len(checks) - passed_count,
        "tests_quantity": len(checks),
        "response_headers": [{"name": k, "value": v} for k, v in headers.items()],
        "tests": checks,
    }
