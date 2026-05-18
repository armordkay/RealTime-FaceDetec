from datetime import datetime, timezone
from zoneinfo import ZoneInfo


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def as_vietnam_time(value: datetime) -> datetime:
    return as_utc(value).astimezone(VIETNAM_TZ)


def vietnam_now() -> datetime:
    return datetime.now(VIETNAM_TZ)


def vietnam_today():
    return vietnam_now().date()


def to_vietnam_iso(value: datetime) -> str:
    return as_vietnam_time(value).isoformat()
