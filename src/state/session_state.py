from __future__ import annotations

from datetime import datetime

import streamlit as st

from models import (
    BackendState,
    DemoAdminState,
    ManualChargeEvent,
    SchedulePauseEvent,
)
from utils import (
    get_current_time_to_nearest_30_minutes,
    MANUAL_CHARGE_DURATION_KEY,
    STATE_KEY,
    DEMO_KEY,
    BASE_TIME_KEY,
    MANUAL_CHARGE_EVENTS_KEY,
    SCHEDULE_PAUSE_EVENTS_KEY,
)


def _session_list(key: str) -> list:
    return st.session_state.setdefault(key, [])


def get_manual_charge_events() -> list[ManualChargeEvent]:
    return _session_list(MANUAL_CHARGE_EVENTS_KEY)


def get_schedule_pause_events() -> list[SchedulePauseEvent]:
    return _session_list(SCHEDULE_PAUSE_EVENTS_KEY)


def set_manual_charge_duration_minutes(minutes: int) -> None:
    st.session_state[MANUAL_CHARGE_DURATION_KEY] = minutes


def get_manual_charge_duration_minutes() -> int:
    return int(st.session_state.get(MANUAL_CHARGE_DURATION_KEY, 60))


def set_demo_state(demo_state: DemoAdminState) -> None:
    st.session_state[DEMO_KEY] = demo_state


def load_demo_state() -> DemoAdminState:
    demo = st.session_state.get(DEMO_KEY)
    if demo is None:
        return DemoAdminState(
            car_is_plugged_in=False,
            current_time=datetime.now(),
        )
    return demo


def get_base_time(now: datetime) -> datetime:
    if BASE_TIME_KEY not in st.session_state:
        st.session_state[BASE_TIME_KEY] = now
    return st.session_state[BASE_TIME_KEY]


def set_backend_state(state: BackendState) -> None:
    st.session_state[STATE_KEY] = state


def get_backend_state() -> BackendState | None:
    return st.session_state.get(STATE_KEY)


def get_demo_state() -> DemoAdminState:
    rounded_time = get_current_time_to_nearest_30_minutes()

    if "simulated_datetime" not in st.session_state:
        st.session_state["simulated_datetime"] = rounded_time

    if "car_is_plugged_in" not in st.session_state:
        st.session_state["car_is_plugged_in"] = True

    return DemoAdminState(
        car_is_plugged_in=st.session_state["car_is_plugged_in"],
        current_time=st.session_state["simulated_datetime"],
    )


def current_demo_state() -> DemoAdminState:
    return DemoAdminState(
        car_is_plugged_in=st.session_state.get("car_is_plugged_in", True),
        current_time=st.session_state["simulated_datetime"],
    )


def toggle_plugged_in() -> None:
    st.session_state["car_is_plugged_in"] = not st.session_state["car_is_plugged_in"]
