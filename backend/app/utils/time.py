from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_shanghai() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def format_datetime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SHANGHAI_TZ)
    return dt.astimezone(SHANGHAI_TZ).strftime(DATETIME_FORMAT)


def format_time_ago(dt: datetime) -> str:
    now = now_shanghai()
    target = dt.replace(tzinfo=SHANGHAI_TZ) if dt.tzinfo is None else dt.astimezone(SHANGHAI_TZ)
    total = max(int((now - target).total_seconds()), 0)

    if total >= 86400:
        d = total // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"
    if total >= 3600:
        h = total // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if total >= 60:
        m = total // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    return "just now"
