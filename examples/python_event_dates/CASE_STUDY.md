# Daily reports lose events near midnight

This is a synthetic, AI-assisted demonstration, not a customer incident.

## Reproduction

An event at `2026-01-14T22:15:00Z` occurred on January 15 in Jerusalem. A January 15 report should include it, but the original code compares the UTC calendar date, January 14.

## Cause and change

The original implementation accepts `time_zone` but never uses it. The correction converts each offset-aware timestamp into the requested IANA zone before comparing dates. It rejects timestamps without an offset because guessing their zone can silently change the report.

No fixed 24-hour window is assumed: local days can span 23 or 25 hours at daylight-saving transitions.

## Acceptance criteria

- Select events whose timestamp becomes `target_day` in `time_zone`.
- Accept ISO timestamps with `Z` or an explicit UTC offset.
- Reject naive timestamps and unknown zones.
- Preserve input order and leave input data unchanged. Returned items refer to the original dictionaries.
- Handle empty input and both daylight-saving transitions.

## Files and verification

- [Original](before.py), [correction](after.py), [patch](fix.patch).
- [Ten regression tests](test_event_filter.py), run against both versions.
- From the repository root: `python3 examples/python_event_dates/test_event_filter.py`.
- Set `DEMO_VERSION=before` to reproduce the failing original behavior on Unix-like shells.

## Scope

This helper takes already validated event dictionaries with an `occurred_at` string and a Python `date` target. Invalid timestamp syntax raises the parser's error. Ingestion validation, database queries, and deployment are outside this example. Time-zone results depend on the installed IANA database; production environments should manage its updates.
