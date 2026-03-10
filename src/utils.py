from datetime import datetime, timedelta, time

# ----------------------------
# Domain / configuration
# ----------------------------

SCHEDULE_START = time(hour=2, minute=0)
SCHEDULE_END = time(hour=5, minute=0)

CHARGE_RATE_PER_HOUR = 0.20
INITIAL_SOC = 0.60

PLOT_HORIZON = timedelta(hours=24)
PLOT_STEP = timedelta(minutes=30)

NEXT_MORNING_AT = time(hour=0, minute=0)

# ----------------------------
# Persistent backend state
# ----------------------------

MANUAL_CHARGE_DURATION_KEY = "manual_charge_duration_minutes"
STATE_KEY = "axle_backend_state"
DEMO_KEY = "axle_demo_state"

BASE_TIME_KEY = "axle_base_time"
MANUAL_CHARGE_EVENTS_KEY = "axle_manual_charge_events"
SCHEDULE_PAUSE_EVENTS_KEY = "axle_schedule_pause_events"

# ----------------------------
# Helper functions
# ----------------------------


def get_current_time_to_nearest_30_minutes():
    """
    Return the current time, rounded to the nearest 30 minutes.
    """
    now = datetime.now()
    minutes = 30 * round(now.minute / 30)
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
