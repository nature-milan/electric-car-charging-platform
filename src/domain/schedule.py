from datetime import datetime, timedelta

from utils import SCHEDULE_START, SCHEDULE_END, NEXT_MORNING_AT


def is_within_schedule_window(ts: datetime) -> bool:
    lt = ts.time()
    return SCHEDULE_START <= lt < SCHEDULE_END


def next_schedule_start(now: datetime) -> datetime:
    candidate = datetime.combine(now.date(), SCHEDULE_START).replace(tzinfo=now.tzinfo)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


def next_morning_cutoff(now: datetime) -> datetime:
    candidate = datetime.combine(now.date(), NEXT_MORNING_AT).replace(tzinfo=now.tzinfo)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate
