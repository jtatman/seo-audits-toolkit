"""Optional deeper security scan via wapiti (pip-installable, pure Python -
no separate runtime/CLI download needed beyond the package itself, unlike
the Node tools the old Django app shelled out to). This actively probes the
target with attack payloads (XSS, SQLi, CSRF, etc.) - only meant to be run
against sites the user owns or is authorized to test, which is why it's a
separate opt-in scan rather than bundled into the passive header check."""

import json
import subprocess
import tempfile
from pathlib import Path

MAX_SCAN_TIME = 300
MAX_ATTACK_TIME = 300


def scan(url):
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "report.json"
        result = subprocess.run(
            [
                "wapiti",
                "-u", url,
                "--scope", "url",
                "--max-scan-time", str(MAX_SCAN_TIME),
                "--max-attack-time", str(MAX_ATTACK_TIME),
                "-f", "json",
                "-o", str(report_path),
                "--no-bugreport",
            ],
            capture_output=True,
            text=True,
            timeout=MAX_SCAN_TIME + MAX_ATTACK_TIME + 60,
        )

        if not report_path.exists():
            raise RuntimeError(
                f"wapiti produced no report (exit {result.returncode}): "
                f"{result.stderr[-2000:]}"
            )

        report = json.loads(report_path.read_text())

    findings = []
    for category_dict in (
        report.get("vulnerabilities", {}),
        report.get("anomalies", {}),
    ):
        for category, entries in category_dict.items():
            for entry in entries:
                findings.append(
                    {
                        "category": category,
                        "info": entry.get("info"),
                        "level": entry.get("level"),
                        "path": entry.get("path"),
                    }
                )

    return {
        "crawled_pages": report.get("infos", {}).get("crawled_pages_nbr"),
        "findings_count": len(findings),
        "findings": findings,
    }
