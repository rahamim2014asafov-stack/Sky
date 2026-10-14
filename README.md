# Bug Fix Case Studies

Two small, reproducible demonstrations of diagnosing a bug, fixing it, and checking the behavior with regression tests.

**Disclosure:** These are synthetic examples created with AI assistance. They are not client projects, paid bounties, or evidence of previous commercial work.

| Case | User-visible problem | Fix and evidence |
| --- | --- | --- |
| [Python: local event dates](examples/python_event_dates/CASE_STUDY.md) | A daily report includes or misses events near midnight because it uses the timestamp's date instead of the report's time zone. | Convert aware timestamps to the selected zone; test midnight boundaries and daylight-saving transitions. |
| [JavaScript: URL filters](examples/js_query_filters/CASE_STUDY.md) | A search URL loses `0`, `false`, and empty values; multiple selections become one comma-separated value. | Omit only nullish values and encode array items as repeated parameters. |

Each case includes `before`, `after`, the same tests for both versions, and a unified patch.

## Reproduce

Requirements: Python 3.11 or later, Node.js 20 or later, and an installed IANA time-zone database (normally included on Linux/macOS). No third-party Python or JavaScript packages are required.

From this directory:

```sh
python3 scripts/verify.py
```

The command first checks that the original code fails behavioral tests, then checks that the corrected code passes the same tests. An expected failure in the `before` version is part of the demonstration. A missing test runner, import error, or unexpected result makes verification fail.

The generated [verification report](verification/report.json) records runtime versions and results; full test output is in `verification/`. Tests cover the stated contracts, not every possible production environment.

## Review order

1. Read the case study and its acceptance criteria.
2. Inspect `fix.patch` for the change.
3. Run the tests and inspect the captured output.

Real customer work would also require an agreed scope, permission to access and process the code, a reproducible issue, and acceptance by the repository owner.
