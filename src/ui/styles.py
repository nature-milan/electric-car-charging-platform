import streamlit as st

BASE_CSS = """
<style>
.block-container {
    padding-top: 2.4rem;
    padding-bottom: 1.5rem;
}

.panel-title {
    text-align: center;
    font-size: 40px;
    font-weight: 800;
    line-height: 1.2;
    margin: 0 0 1.4rem 0;
    padding-top: 0.15rem;
    letter-spacing: 0.2px;
}

.big-metric-title {
    font-size: 20px;
    font-weight: 700;
    text-align: center;
    margin: 0;
    opacity: 0.95;
}

.big-metric-value {
    font-size: 24px;
    font-weight: 800;
    line-height: 1.2;
    text-align: center;
    margin: 0;
}

.big-metric-sub {
    opacity: 0.82;
    font-size: 14px;
    line-height: 1.45;
    text-align: center;
    margin: 0;
    max-width: 95%;
}

.overview-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.overview-card-center {
    text-align: center;
}

div[data-testid="stTimeInput"] button {
    min-height: 52px !important;
}

div[data-testid="stButton"] > button[kind] {
    border-radius: 14px;
}

div[data-testid="stButton"] > button[kind][aria-label="plugged_in_toggle_button"] {
    height: 30px !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.st-key-plugged_in_toggle_button button {
    height: 100px !important;
    border-radius: 14px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: background-color 0.28s ease, border-color 0.28s ease, color 0.28s ease, transform 0.08s ease;
}

.st-key-plugged_in_toggle_button button p,
.st-key-plugged_in_toggle_button button span {
    font-size: 35px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
}

.st-key-plugged_in_toggle_button button:hover {
    transform: translateY(-1px);
}
.manual-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
    padding: 0.15rem 0;
}

.manual-card-title {
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 0.8rem;
}

.manual-card-sub {
    text-align: center;
    font-size: 18px;
    opacity: 0.82;
    line-height: 1.35;
    margin-top: 0.55rem;
}

.st-key-manual_charge_toggle_button button {
    height: 100px !important;
    min-height: 100px !important;
    border-radius: 14px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: background-color 0.28s ease, border-color 0.28s ease, color 0.28s ease, transform 0.08s ease;
}

.st-key-manual_charge_toggle_button button p,
.st-key-manual_charge_toggle_button button span {
    font-size: 34px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    color: white !important;
}

.st-key-manual_charge_toggle_button button:hover {
    transform: translateY(-1px);
}

</style>
"""

OVERVIEW_CARD_CSS = """
<style>
.overview-card-title {
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 1.1rem;
}
.overview-card-value {
    text-align: center;
    font-size: 24px;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 0.35rem;
}
.overview-card-sub {
    text-align: center;
    font-size: 24px;
    opacity: 0.82;
    line-height: 1.4;
}
</style>
"""


def render_base_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)


def render_overview_card_css() -> None:
    st.markdown(OVERVIEW_CARD_CSS, unsafe_allow_html=True)


def render_button_theme(key: str, bg: str, border: str) -> None:
    st.markdown(
        f"""
        <style>
        .st-key-{key} button {{
            background-color: {bg} !important;
            color: white !important;
            border: 1px solid {border} !important;
            box-shadow: none !important;
        }}

        .st-key-{key} button p,
        .st-key-{key} button span {{
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
