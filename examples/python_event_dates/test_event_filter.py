"""Run the same behavioral tests against either demonstration version."""

import copy
import importlib.util
import os
from pathlib import Path
import unittest
from datetime import date
from zoneinfo import ZoneInfoNotFoundError


version = os.environ.get("DEMO_VERSION", "after")
if version not in {"before", "after"}:
    raise ValueError("DEMO_VERSION must be before or after")
spec = importlib.util.spec_from_file_location(
    "event_filter", Path(__file__).with_name(f"{version}.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
select = module.filter_events_for_local_day


def event(event_id, timestamp):
    return {"id": event_id, "occurred_at": timestamp}


class EventFilterTests(unittest.TestCase):
    def test_utc_day_boundaries(self):
        events = [
            event("previous", "2026-06-09T23:59:59Z"),
            event("start", "2026-06-10T00:00:00Z"),
            event("end", "2026-06-10T23:59:59Z"),
            event("next", "2026-06-11T00:00:00Z"),
        ]
        self.assertEqual(select(events, date(2026, 6, 10), "UTC"), events[1:3])

    def test_previous_utc_date_can_belong_to_local_day(self):
        events = [event("early", "2026-01-14T22:15:00Z")]
        self.assertEqual(
            select(events, date(2026, 1, 15), "Asia/Jerusalem"), events
        )

    def test_late_utc_event_can_belong_to_next_local_day(self):
        events = [event("tomorrow", "2026-01-15T22:15:00Z")]
        self.assertEqual(
            select(events, date(2026, 1, 15), "Asia/Jerusalem"), []
        )

    def test_explicit_offset_is_normalized_to_report_zone(self):
        events = [event("offset", "2026-01-15T00:30:00+09:00")]
        self.assertEqual(select(events, date(2026, 1, 14), "UTC"), events)

    def test_spring_forward_day_has_23_hours(self):
        events = [
            event("previous", "2026-03-08T04:59:59Z"),
            event("start", "2026-03-08T05:00:00Z"),
            event("end", "2026-03-09T03:59:59Z"),
            event("next", "2026-03-09T04:00:00Z"),
        ]
        self.assertEqual(
            select(events, date(2026, 3, 8), "America/New_York"), events[1:3]
        )

    def test_fall_back_includes_both_repeated_hours_and_late_boundary(self):
        events = [
            event("start", "2026-11-01T04:00:00Z"),
            event("first_0130", "2026-11-01T05:30:00Z"),
            event("second_0130", "2026-11-01T06:30:00Z"),
            event("end", "2026-11-02T04:59:59Z"),
            event("next", "2026-11-02T05:00:00Z"),
        ]
        self.assertEqual(
            select(events, date(2026, 11, 1), "America/New_York"), events[:4]
        )

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            select([event("ambiguous", "2026-01-15T12:00:00")], date(2026, 1, 15), "UTC")

    def test_input_order_and_values_are_preserved(self):
        events = [
            event("later", "2026-06-10T18:00:00Z"),
            event("outside", "2026-06-11T01:00:00Z"),
            event("earlier", "2026-06-10T03:00:00Z"),
        ]
        original = copy.deepcopy(events)
        self.assertEqual(select(events, date(2026, 6, 10), "UTC"), [events[0], events[2]])
        self.assertEqual(events, original)

    def test_empty_input(self):
        self.assertEqual(select([], date(2026, 6, 10), "UTC"), [])

    def test_invalid_zone_is_rejected_even_for_empty_input(self):
        with self.assertRaises(ZoneInfoNotFoundError):
            select([], date(2026, 6, 10), "Invalid/Example")


if __name__ == "__main__":
    unittest.main(verbosity=2)
