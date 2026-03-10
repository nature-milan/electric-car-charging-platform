from __future__ import annotations

from datetime import time, timedelta
from collections.abc import Callable

import streamlit as st

from backend import (
    get_max_manual_charge_minutes,
    handle_start_charge,
    handle_stop_charge,
)
from domain.schedule import is_within_schedule_window, next_schedule_start
from models import BackendState, DemoAdminState
from ui.formatters import format_time, format_datetime
from ui.styles import render_button_theme, render_overview_card_css
from state.session_state import set_manual_charge_duration_minutes


# Battery charge bar
def render_soc_bar(soc: float) -> None:
    pct = max(0.0, min(1.0, soc)) * 100.0
    if pct < 20:
        color = "#ff4d4f"
    elif pct <= 80:
        color = "#faad14"
    else:
        color = "#52c41a"

    st.markdown(
        f"""
        <div style="width: 100%; background: rgba(255,255,255,0.10); border-radius: 10px; padding: 3px; margin-top: 10px;">
          <div style="width: {pct:.1f}%; background: {color}; height: 14px; border-radius: 8px;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Section at the top of the page which has 4 subsections
def render_status_panel(
    *,
    demo_state: DemoAdminState,
    car_is_charging: bool,
    charge_is_override: bool,
    snap: BackendState | None,
    on_toggle_plugged_in: Callable[[], None],
) -> None:
    st.markdown(
        '<div class="panel-title">Charge Control Panel</div>',
        unsafe_allow_html=True,
    )

    render_overview_card_css()

    c1, c2, c3, c4 = st.columns(4, gap="medium", border=True)

    # Drop down to select simulation time
    with c1:
        st.markdown(
            '<div class="overview-card overview-card-center">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="overview-card-title">Simulated Time</div>',
            unsafe_allow_html=True,
        )

        all_times = [time(hour=h, minute=m) for h in range(24) for m in (0, 30)]
        anchor_dt = demo_state.current_time
        current_time_value = anchor_dt.time()

        current_index = all_times.index(current_time_value)
        next_index = (current_index + 1) % len(all_times)
        time_options = all_times[next_index:] + all_times[:next_index]

        if current_time_value in time_options:
            time_options.remove(current_time_value)
        time_options.append(current_time_value)

        selected_index = len(time_options) - 1

        _, mid, _ = st.columns([4, 8, 4])

        with mid:
            picked_time = st.selectbox(
                "Simulated Time",
                options=time_options,
                index=selected_index,
                format_func=lambda t: format_time(t),
                key="current_time_value",
                label_visibility="collapsed",
            )

        if picked_time != current_time_value:
            current_minutes = anchor_dt.hour * 60 + anchor_dt.minute
            picked_minutes = picked_time.hour * 60 + picked_time.minute
            delta_minutes = (picked_minutes - current_minutes) % (24 * 60)

            new_dt = anchor_dt + timedelta(minutes=delta_minutes)
            demo_state.current_time = new_dt
            st.session_state["simulated_datetime"] = new_dt
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # Battery charge bar graphic
    with c2:
        st.markdown(
            '<div class="overview-card overview-card-center">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="overview-card-title">Battery Charge</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="overview-card-value">{snap.soc * 100:.0f}%</div>',
            unsafe_allow_html=True,
        )

        render_soc_bar(snap.soc)
        st.markdown("</div>", unsafe_allow_html=True)

    # Status update - Vehicle plugged in and charging or not
    with c3:
        st.markdown(
            '<div class="overview-card overview-card-center">',
            unsafe_allow_html=True,
        )

        if not demo_state.car_is_plugged_in:
            plugged_mode = "❌"
            charge_mode = "❌"
            sub = "Plug in the vehicle to allow scheduled or manual charging."
        elif car_is_charging and charge_is_override:
            plugged_mode = "✅"
            charge_mode = "✅ (manual)"
            sub = f"Manual charge ends at {format_datetime(snap.override_until)}."
        elif car_is_charging:
            plugged_mode = "✅"
            charge_mode = "✅ (scheduled)"
            sub = "Following the scheduled charging window."
        else:
            plugged_mode = "✅"
            charge_mode = "❌"
            if snap.schedule_disabled_until is not None:
                sub = f"Schedule paused until {format_datetime(snap.schedule_disabled_until)}."
            elif is_within_schedule_window(demo_state.current_time):
                sub = "Inside the schedule window, but charging is currently off."
            else:
                sub = f"Next schedule starts at {format_datetime(next_schedule_start(demo_state.current_time))}."

        st.markdown(
            f'<div class="overview-card-value">Plugged in: {plugged_mode} Charging: {charge_mode}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="overview-card-sub">{sub}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    # Button to plug in / unplug vehicle
    with c4:
        plugged = st.session_state["car_is_plugged_in"]
        button_text = "Click to Unplug" if plugged else "Click to Plug In"

        if plugged:
            btn_bg = "#dc2626"
            btn_border = "#b91c1c"
        else:
            btn_bg = "#16a34a"
            btn_border = "#15803d"

        render_button_theme("plugged_in_toggle_button", btn_bg, btn_border)

        st.button(
            button_text,
            key="plugged_in_toggle_button",
            width="stretch",
            on_click=on_toggle_plugged_in,
        )

        demo_state.car_is_plugged_in = st.session_state["car_is_plugged_in"]


# Manual charging controls at the bottom of the screen
def render_controls(
    *,
    car_is_plugged_in: bool,
    car_is_charging: bool,
    charge_is_override: bool,
    snap: BackendState,
) -> None:
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    max_minutes = get_max_manual_charge_minutes(snap.soc)
    duration_values = list(range(30, max_minutes + 1, 30))

    def _format_duration_label(minutes: int) -> str:
        if minutes == 30:
            return "30 mins"
        if minutes % 60 == 0:
            hours = minutes // 60
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
        return f"{minutes / 60:.1f} hours"

    duration_options = {
        _format_duration_label(minutes): minutes for minutes in duration_values
    }

    if not duration_options:
        st.session_state["manual_charge_duration_label"] = None
    else:
        available_labels = list(duration_options.keys())
        if (
            "manual_charge_duration_label" not in st.session_state
            or st.session_state["manual_charge_duration_label"] not in available_labels
        ):
            st.session_state["manual_charge_duration_label"] = (
                "1 hour" if "1 hour" in available_labels else available_labels[-1]
            )

    c1, c2 = st.columns([1, 3], gap="medium", border=True)

    # Drop down to select manual charging period
    with c1:
        st.markdown('<div class="manual-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="manual-card-title">Charging Time</div>',
            unsafe_allow_html=True,
        )

        _, d1, _ = st.columns([6, 8, 6])

        with d1:
            if duration_options:
                selected_label = st.selectbox(
                    "Charging Time",
                    options=list(duration_options.keys()),
                    key="manual_charge_duration_label",
                    label_visibility="collapsed",
                )
                set_manual_charge_duration_minutes(duration_options[selected_label])
            else:
                selected_label = None

        if selected_label is not None:
            st.markdown(
                f'<div class="manual-card-sub">Selected: {selected_label}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="manual-card-sub">Battery already full</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # Button to strat/ stop both manual or scheduled charging
    with c2:
        st.markdown('<div class="manual-card">', unsafe_allow_html=True)

        can_start_manual = (
            car_is_plugged_in
            and (not car_is_charging)
            and (get_max_manual_charge_minutes(snap.soc) >= 30)
        )

        if car_is_charging:
            button_text = "Click to Stop Charging"
            button_bg = "#dc2626"
            button_border = "#b91c1c"
            button_disabled = False
            button_action = handle_stop_charge

            if charge_is_override:
                button_help = (
                    "Stops the manual charge and returns to normal schedule behaviour."
                )
            else:
                button_help = "Stops scheduled charging and pauses the schedule until tomorrow morning."
        else:
            if selected_label is not None:
                button_text = (
                    f"Click to start a Manual Charge for {selected_label.lower()}"
                )
            else:
                button_text = "Click to start a Manual Charge"

            button_bg = "#16a34a"
            button_border = "#15803d"
            button_disabled = not can_start_manual
            button_action = handle_start_charge

            if not car_is_plugged_in:
                button_help = "Plug in to start charging."
            elif not duration_options:
                button_text = "Battery already full"
                button_help = ""
            else:
                button_help = f"Charge immediately for {selected_label.lower()}."

        render_button_theme("manual_charge_toggle_button", button_bg, button_border)

        if st.button(
            button_text,
            key="manual_charge_toggle_button",
            disabled=button_disabled,
            help=button_help,
            width="stretch",
        ):
            button_action()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
