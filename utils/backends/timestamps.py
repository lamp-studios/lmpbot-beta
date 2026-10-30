import re
from datetime import datetime, timezone

_FRACTION = re.compile(r"\.(\d+)")


def to_iso(ts: int) -> str:
    """Epoch ms as the ISO string JavaScript's toISOString() produces, e.g. 2026-01-30T08:00:00.000Z."""
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(value: str) -> int:
    """Epoch ms from an ISO timestamp, as written by JavaScript, Postgres or to_iso().

    Python 3.10's fromisoformat only takes 3 or 6 fractional digits and no "Z",
    while Postgres trims trailing zeros, so both are normalised first.
    """
    text = str(value).strip().replace(" ", "T", 1).replace("Z", "+00:00")
    text = _FRACTION.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), text, count=1)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
