from __future__ import annotations

from datetime import datetime, timedelta

from domain.schedule import is_within_schedule_window, next_morning_cutoff
from models import (
    BackendState,
    ChargerState,
    CombinedState,
    DemoAdminState,
    ManualChargeEvent,
    SchedulePauseEvent,
)
from state.session_state import (
    get_base_time,
    get_manual_charge_duration_minutes,
    get_manual_charge_events,
    get_schedule_pause_events,
    set_backend_state,
    current_demo_state,
)
from utils import CHARGE_RATE_PER_HOUR, INITIAL_SOC, PLOT_HORIZON, PLOT_STEP


def _event_end_at(
    ts: datetime,
    events: list[ManualChargeEvent] | list[SchedulePauseEvent],
) -> datetime | None:
    for event in events:
        if event.start <= ts < event.end:
            return event.end
    return None


def _add_event(
    events: list[ManualChargeEvent] | list[SchedulePauseEvent],
    event: ManualChargeEvent | SchedulePauseEvent,
) -> None:
    events.append(event)
    events.sort(key=lambda e: e.start)


def _truncate_active_manual_charge(now: datetime) -> None:
    events = get_manual_charge_events()
    for i in range(len(events) - 1, -1, -1):
        event = events[i]
        if event.start <= now < event.end:
            events[i] = ManualChargeEvent(start=event.start, end=now)
            return


def _clamp_soc(soc: float) -> float:
    return max(0.0, min(1.0, soc))


def _time_until_full(soc: float) -> timedelta:
    return timedelta(hours=max(0.0, 1.0 - _clamp_soc(soc)) / CHARGE_RATE_PER_HOUR)


def _expire_windows(state: BackendState, now: datetime) -> None:
    """
    Removes expired manual override or schedule pause windows
    once the simulated time passes their end time.
    """
    if state.override_until is not None and now >= state.override_until:
        state.override_until = None
    if (
        state.schedule_disabled_until is not None
        and now >= state.schedule_disabled_until
    ):
        state.schedule_disabled_until = None


def _charger_state_at(
    demo_state: DemoAdminState,
    state: BackendState,
    now: datetime,
) -> ChargerState:
    """
    Determines whether the car should be charging at a specific moment
    and whether that charging is manual or scheduled.
    """
    if not demo_state.car_is_plugged_in or state.soc >= 1.0:
        return ChargerState(car_is_charging=False, charge_is_override=False)

    override_until = _event_end_at(now, get_manual_charge_events())
    if (
        state.override_until is not None and now < state.override_until
    ) or override_until:
        return ChargerState(car_is_charging=True, charge_is_override=True)

    schedule_paused = (
        state.schedule_disabled_until is not None
        and now < state.schedule_disabled_until
    ) or _event_end_at(now, get_schedule_pause_events()) is not None

    return ChargerState(
        car_is_charging=is_within_schedule_window(now) and not schedule_paused,
        charge_is_override=False,
    )


def _apply_charging_step(
    state: BackendState,
    *,
    start: datetime,
    end: datetime,
    charge_is_override: bool,
) -> None:
    """
    Applies the SOC increase for one charging interval and handles the
    special case where the battery reaches full before the interval ends.
    """
    step = end - start
    time_to_full = _time_until_full(state.soc)

    if time_to_full <= step:
        full_at = start + time_to_full
        state.soc = 1.0
        if charge_is_override:
            state.override_until = None
        else:
            state.schedule_disabled_until = next_morning_cutoff(full_at)
        return

    hours = step.total_seconds() / 3600.0
    state.soc = _clamp_soc(state.soc + CHARGE_RATE_PER_HOUR * hours)


def _replay_interval(
    demo_state: DemoAdminState,
    state: BackendState,
    start: datetime,
    end: datetime,
) -> None:
    """
    Simulates the battery and charger behaviour between two timestamps by
    advancing time in 30-minute steps and applying charging logic when appropriate.
    """
    current = start
    while current < end:
        next_time = min(current + PLOT_STEP, end)
        _expire_windows(state, current)

        charger = _charger_state_at(demo_state, state, current)
        if charger.car_is_charging:
            _apply_charging_step(
                state,
                start=current,
                end=next_time,
                charge_is_override=charger.charge_is_override,
            )

        current = next_time

    _expire_windows(state, end)


def _rebuild_state(demo_state: DemoAdminState) -> BackendState:
    """
    Reconstructs the current battery state by starting from the initial SOC
    and replaying all charging behaviour from the simulation start time up
    to the current simulated time.
    """
    now = demo_state.current_time
    rebuilt = BackendState(
        soc=INITIAL_SOC,
        override_until=None,
        schedule_disabled_until=None,
    )

    base_time = get_base_time(now)
    if now > base_time:
        _replay_interval(
            DemoAdminState(car_is_plugged_in=True, current_time=now),
            rebuilt,
            base_time,
            now,
        )

    rebuilt.override_until = _event_end_at(now, get_manual_charge_events())
    rebuilt.schedule_disabled_until = _event_end_at(now, get_schedule_pause_events())
    set_backend_state(rebuilt)
    return rebuilt


def _load_state(
    demo_state: DemoAdminState | None = None,
) -> tuple[DemoAdminState, BackendState]:
    demo_state = demo_state or current_demo_state()
    return demo_state, _rebuild_state(demo_state)


def get_backend_snapshot() -> BackendState:
    _, state = _load_state()
    return state


def get_max_manual_charge_minutes(soc: float) -> int:
    """
    Maximum minutes for manual charging rounded to 30 mins.
    """
    if soc >= 1.0:
        return 0
    remaining_minutes = int(((1.0 - _clamp_soc(soc)) / CHARGE_RATE_PER_HOUR) * 60)
    return (remaining_minutes // 30) * 30


def get_car_state(demo_state: DemoAdminState) -> ChargerState:
    demo_state, state = _load_state(demo_state)
    return _charger_state_at(demo_state, state, demo_state.current_time)


def get_future_states() -> list[CombinedState]:
    demo_state, state = _load_state()
    sim_state = BackendState(
        soc=state.soc,
        override_until=state.override_until,
        schedule_disabled_until=state.schedule_disabled_until,
    )

    states: list[CombinedState] = []
    current = demo_state.current_time
    end = current + PLOT_HORIZON

    while current <= end:
        charger = _charger_state_at(demo_state, sim_state, current)
        states.append(
            CombinedState(time=current, soc=sim_state.soc, charger_state=charger)
        )

        next_time = current + PLOT_STEP
        if demo_state.car_is_plugged_in:
            _replay_interval(
                DemoAdminState(car_is_plugged_in=True, current_time=current),
                sim_state,
                current,
                next_time,
            )
        current = next_time

    return states


def handle_start_charge() -> None:
    demo_state, state = _load_state()
    if not demo_state.car_is_plugged_in or state.soc >= 1.0:
        return

    end = demo_state.current_time + timedelta(
        minutes=get_manual_charge_duration_minutes()
    )
    _add_event(
        get_manual_charge_events(),
        ManualChargeEvent(start=demo_state.current_time, end=end),
    )
    state.override_until = end
    set_backend_state(state)


def handle_stop_charge() -> None:
    demo_state, state = _load_state()
    now = demo_state.current_time
    charger = _charger_state_at(demo_state, state, now)

    if not charger.car_is_charging:
        return

    if charger.charge_is_override:
        _truncate_active_manual_charge(now)
        state.override_until = None
    else:
        pause_until = next_morning_cutoff(now)
        _add_event(
            get_schedule_pause_events(),
            SchedulePauseEvent(start=now, end=pause_until),
        )
        state.schedule_disabled_until = pause_until

    set_backend_state(state)
