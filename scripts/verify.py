"""Reproduce both bugs, verify both fixes, and save reviewable evidence."""

import difflib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "verification"


def run(command, version):
    env = dict(os.environ, DEMO_VERSION=version, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=60, check=False,
    )


def counts(case, output):
    if case == "python_event_dates":
        total = re.search(r"Ran (\d+) tests?", output)
        failures = re.search(r"failures=(\d+)", output)
        errors = re.search(r"errors=(\d+)", output)
        if not total or errors:
            raise RuntimeError("Python tests did not complete without execution errors")
        failed = int(failures.group(1)) if failures else 0
        return int(total.group(1)), failed
    total = re.search(r"^# tests (\d+)$", output, re.MULTILINE)
    failed = re.search(r"^# fail (\d+)$", output, re.MULTILINE)
    if not total or not failed or "ERR_MODULE_NOT_FOUND" in output:
        raise RuntimeError("JavaScript tests did not produce a complete report")
    return int(total.group(1)), int(failed.group(1))


def main():
    OUTPUT.mkdir(exist_ok=True)
    cases = [
        ("python_event_dates", "py", 10, [sys.executable, "examples/python_event_dates/test_event_filter.py"]),
        ("js_query_filters", "mjs", 9, ["node", "--test", "--test-reporter=tap", "examples/js_query_filters/test_query.mjs"]),
    ]
    report = {
        "kind": "synthetic AI-assisted demonstrations",
        "python": platform.python_version(),
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "cases": {},
    }
    for case, extension, expected_count, command in cases:
        results = {}
        for version in ("before", "after"):
            result = run(command, version)
            (OUTPUT / f"{case}-{version}.txt").write_text(result.stdout, encoding="utf-8")
            total, failed = counts(case, result.stdout)
            expected = (
                total == expected_count
                and ((version == "before" and result.returncode == 1 and failed > 0)
                     or (version == "after" and result.returncode == 0 and failed == 0))
            )
            results[version] = {
                "tests": total, "passed": total - failed, "failed": failed,
                "exit_code": result.returncode, "expected_result": expected,
            }
            print(f"{case} / {version}: {total - failed}/{total} passed; expected={expected}")
            if not expected:
                raise RuntimeError(f"Unexpected result: {case}/{version}; inspect verification logs")
        report["cases"][case] = results
        folder = ROOT / "examples" / case
        before = (folder / f"before.{extension}").read_text(encoding="utf-8")
        after = (folder / f"after.{extension}").read_text(encoding="utf-8")
        patch = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"before.{extension}", tofile=f"after.{extension}",
        ))
        (folder / "fix.patch").write_text(patch, encoding="utf-8")
    report["verified"] = True
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Verified: both original bugs reproduce; both corrected versions pass.")


if __name__ == "__main__":
    main()
