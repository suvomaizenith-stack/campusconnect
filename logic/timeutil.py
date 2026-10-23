"""Time helpers: store UTC, show IST."""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_ist(dt: datetime) -> datetime:
    """Convert an aware datetime to IST."""
    return dt.astimezone(IST)


def fmt_ist(dt: datetime | None) -> str:
    """Format like '12 Mar, 4:05 PM IST'."""
    if dt is None:
        return ""
    d = to_ist(dt)
    return f"{d.day} {d:%b}, {d.strftime('%I:%M %p').lstrip('0')} IST"


def time_ago(dt: datetime | None, now: datetime | None = None) -> str:
    """Human 'time ago': 'just now', '5 min ago', '3 h ago', '2 days ago'."""
    if dt is None:
        return ""
    secs = int(((now or now_utc()) - dt).total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60} min ago"
    if secs < 86400:
        return f"{secs // 3600} h ago"
    return f"{secs // 86400} days ago"


def eta_text(eta_at: datetime | None, now: datetime | None = None) -> str:
    """Friendly ETA: 'about 5 h (by 4:05 PM IST)', 'any moment now', or 'not set yet'."""
    if eta_at is None:
        return "not set yet"
    secs = int((eta_at - (now or now_utc())).total_seconds())
    if secs <= 0:
        return "any moment now"
    hours = round(secs / 3600)
    span = f"about {hours} h" if hours >= 1 else f"about {max(1, secs // 60)} min"
    return f"{span} (by {fmt_ist(eta_at)})"


def hours_from_now(hours: float) -> datetime:
    return now_utc() + timedelta(hours=hours)
