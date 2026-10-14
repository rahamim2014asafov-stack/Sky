"""Original demonstration implementation: ignores the report's time zone."""

from datetime import date, datetime


def filter_events_for_local_day(
    events: list[dict], target_day: date, time_zone: str
) -> list[dict]:
    return [
        event
        for event in events
        if datetime.fromisoformat(event["occurred_at"]).date() == target_day
    ]
