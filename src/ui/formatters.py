from datetime import datetime


def format_time(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%H:%M")


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%H:%M %d-%m-%Y")
