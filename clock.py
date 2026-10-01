"""
The clock the code reads, as naive datetimes (no tzinfo), the form the stored
timestamps (created_at, notified_at, expires_at, ...) already use.
"""
from datetime import UTC, datetime


def utc_now():
    """Current UTC time without tzinfo. Replaces the deprecated datetime.utcnow()."""
    return datetime.now(UTC).replace(tzinfo=None)
