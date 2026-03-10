from __future__ import annotations

import streamlit as st

from backend import (
    get_car_state,
    get_future_states,
)
from plotting import plot_upcoming_charges
from ui.components import render_controls, render_status_panel
from ui.styles import render_base_css
from state.session_state import get_backend_state, toggle_plugged_in, get_demo_state

st.set_page_config(page_title="Charging Schedule", layout="wide")

render_base_css()

if __name__ == "__main__":
    demo_state = get_demo_state()

    # First render/update the top controls
    initial_car_state = get_car_state(demo_state)
    initial_snap = get_backend_state()

    render_status_panel(
        demo_state=demo_state,
        car_is_charging=initial_car_state.car_is_charging,
        charge_is_override=initial_car_state.charge_is_override,
        snap=initial_snap,
        on_toggle_plugged_in=toggle_plugged_in,
    )

    # Commit elapsed charging up to the selected simulated time
    car_state = get_car_state(demo_state)
    snap = get_backend_state()

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    st.plotly_chart(
        plot_upcoming_charges(
            get_future_states(),
            current_time=demo_state.current_time,
        ),
        width="stretch",
        config={"displayModeBar": False},
    )

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    render_controls(
        car_is_plugged_in=demo_state.car_is_plugged_in,
        car_is_charging=car_state.car_is_charging,
        charge_is_override=car_state.charge_is_override,
        snap=snap,
    )
