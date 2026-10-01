"""
The two clocks the code reads, both as naive datetimes (no tzinfo):

- utc_now() for stored timestamps (created_at, notified_at, expires_at, ...).
- local_now() for business dates and times. Bookings are stored as the
  restaurant's wall-clock date and time ("2026-10-02", "20:00"), and reports
  and analytics count by the restaurant's day, so comparisons with them must
  use the restaurant's clock, not UTC.
"""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from restaurant import load_restaurant


def utc_now():
    """Current UTC time without tzinfo. Replaces the deprecated datetime.utcnow()."""
    return datetime.now(UTC).replace(tzinfo=None)


def local_now():
    """Current wall-clock time at the restaurant (timezone from data/menu.json), without tzinfo."""
    return datetime.now(ZoneInfo(load_restaurant().timezone)).replace(tzinfo=None)
