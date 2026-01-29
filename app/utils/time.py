# app/utils/time.py

from datetime import datetime, timedelta

def start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999000)

def last_n_days_range(days: int) -> tuple[datetime, datetime]:
    """
    Returns (from_time, to_time) normalized for APIs that require full-day bounds.
    """
    now = datetime.utcnow()
    to_time = end_of_day(now)
    from_time = start_of_day(now - timedelta(days=days))
    return from_time, to_time
