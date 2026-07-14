"""Small shared helpers for the db package."""

from __future__ import annotations

from datetime import UTC, datetime


def now_iso() -> str:
    """Current UTC time as a fixed-width, lexically-sortable ISO-8601 string.

    ``datetime.isoformat()`` drops the microseconds field when it's exactly
    zero, which would occasionally break ORDER BY on the TEXT timestamp
    columns. Formatting explicitly keeps every timestamp the same width.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
