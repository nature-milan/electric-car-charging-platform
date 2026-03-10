from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
from plotly.graph_objs import Figure

from models import CombinedState, ChargeSpan, WindowSpan
from domain.schedule import is_within_schedule_window
from utils import PLOT_STEP


def _compute_charge_spans(df: pd.DataFrame) -> list[ChargeSpan]:
    """
    Merge contiguous charging blocks into spans so we can draw one vrect + label per span.
    A span is contiguous if each block is exactly PLOT_STEP apart and shares override flag.
    """
    spans: list[ChargeSpan] = []
    if df.empty:
        return spans

    # We treat each row as representing the interval [Time, Time + PLOT_STEP)
    active = df[df["Car is Charging"]].copy()
    if active.empty:
        return spans

    active = active.sort_values("Time").reset_index(drop=True)

    span_start = active.loc[0, "Time"].to_pydatetime()
    span_override = bool(active.loc[0, "Charge is Override"])
    prev_t = span_start

    for i in range(1, len(active)):
        t = active.loc[i, "Time"].to_pydatetime()
        is_override = bool(active.loc[i, "Charge is Override"])

        contiguous = (t - prev_t) == PLOT_STEP
        same_kind = is_override == span_override

        if contiguous and same_kind:
            prev_t = t
            continue

        # close current span
        spans.append(
            ChargeSpan(
                start=span_start, end=prev_t + PLOT_STEP, is_override=span_override
            )
        )

        # start new span
        span_start = t
        span_override = is_override
        prev_t = t

    spans.append(
        ChargeSpan(start=span_start, end=prev_t + PLOT_STEP, is_override=span_override)
    )
    return spans


def _compute_scheduled_window_spans(df: pd.DataFrame) -> list[WindowSpan]:
    """
    Compute contiguous schedule-window spans based purely on clock time,
    so the graph always shows when the scheduled charging window is.
    """
    spans: list[WindowSpan] = []
    if df.empty:
        return spans

    scheduled = df[
        df["Time"].apply(lambda t: is_within_schedule_window(t.to_pydatetime()))
    ].copy()
    if scheduled.empty:
        return spans

    scheduled = scheduled.sort_values("Time").reset_index(drop=True)

    span_start = scheduled.loc[0, "Time"].to_pydatetime()
    prev_t = span_start

    for i in range(1, len(scheduled)):
        t = scheduled.loc[i, "Time"].to_pydatetime()
        contiguous = (t - prev_t) == PLOT_STEP

        if contiguous:
            prev_t = t
            continue

        spans.append(WindowSpan(start=span_start, end=prev_t + PLOT_STEP))
        span_start = t
        prev_t = t

    spans.append(WindowSpan(start=span_start, end=prev_t + PLOT_STEP))
    return spans


def _build_plot_df(states: list[CombinedState]) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "Time": [s.time for s in states],
            "State of Charge": [s.soc for s in states],
            "Car is Charging": [s.charger_state.car_is_charging for s in states],
            "Charge is Override": [s.charger_state.charge_is_override for s in states],
        }
    )
    df["Time"] = pd.to_datetime(df["Time"])
    return df.sort_values("Time").reset_index(drop=True)


def _get_plot_window(current_time: datetime) -> tuple[datetime, datetime, datetime]:
    x_now = pd.to_datetime(current_time).to_pydatetime()
    x_start = x_now - timedelta(hours=1)
    x_end = x_now + timedelta(hours=24)
    return x_now, x_start, x_end


def _add_hour_lines(fig: Figure, x_start: datetime, x_end: datetime) -> None:
    hour_lines = pd.date_range(
        pd.to_datetime(x_start).replace(minute=0, second=0, microsecond=0),
        pd.to_datetime(x_end),
        freq="1h",
    ).to_pydatetime()

    for h in hour_lines:
        if x_start < h < x_end:
            fig.add_vline(
                x=h,
                line_width=1,
                line_dash="dot",
                line_color="rgba(255,255,255,0.06)",
                layer="below",
            )


def _add_plot_boundaries(fig: Figure, x_start: datetime, x_end: datetime) -> None:
    boundary_inset = timedelta(minutes=1)
    x_left_boundary = x_start + boundary_inset
    x_right_boundary = x_end - boundary_inset

    fig.add_vline(
        x=x_left_boundary,
        line_width=1,
        line_color="rgba(255,255,255,0.14)",
        layer="below",
    )
    fig.add_vline(
        x=x_right_boundary,
        line_width=1,
        line_color="rgba(255,255,255,0.14)",
        layer="below",
    )
    fig.add_hline(
        y=0,
        line_width=1,
        line_color="rgba(255,255,255,0.14)",
        layer="below",
    )
    fig.add_hline(
        y=1,
        line_width=1,
        line_color="rgba(255,255,255,0.14)",
        layer="below",
    )


def _get_midnight_points(x_start: datetime, x_end: datetime) -> list[datetime]:
    return list(
        pd.date_range(
            pd.to_datetime(x_start).normalize(),
            pd.to_datetime(x_end).normalize() + timedelta(days=1),
            freq="D",
        ).to_pydatetime()
    )


def _add_midnight_lines(
    fig: Figure, x_start: datetime, x_end: datetime
) -> list[datetime]:
    midnight_points = _get_midnight_points(x_start, x_end)

    for m in midnight_points:
        if x_start < m < x_end:
            fig.add_vline(
                x=m,
                line_width=5,
                line_dash="solid",
                line_color="rgba(255,255,255,0.15)",
                layer="below",
            )

    return midnight_points


def _build_tick_values(
    x_now: datetime, x_start: datetime, x_end: datetime
) -> list[datetime]:
    aligned_start = x_start.replace(minute=0, second=0, microsecond=0)
    if aligned_start.hour % 2 == 1:
        aligned_start = aligned_start - timedelta(hours=1)

    tick_vals = list(pd.date_range(aligned_start, x_end, freq="2h").to_pydatetime())

    now_index = None
    for i, t in enumerate(tick_vals):
        if abs((t - x_now).total_seconds()) <= 60:
            now_index = i
            break

    if now_index is None:
        tick_vals.append(x_now)
        tick_vals.sort()

    return tick_vals


def _configure_axes(
    fig: Figure,
    *,
    x_start: datetime,
    x_end: datetime,
    tick_vals: list[datetime],
) -> None:
    tick_text = [t.strftime("%H:%M") for t in tick_vals]

    fig.update_xaxes(
        title_text=None,
        type="date",
        range=[x_start, x_end],
        tickmode="array",
        tickangle=-50,
        tickvals=tick_vals,
        ticktext=tick_text,
        tickfont=dict(size=18),
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(255,255,255,0.06)",
        dtick=3600000,
        showline=False,
    )

    fig.update_yaxes(
        title_text="<b>State of Charge</b>",
        title_font=dict(size=18),
        tickfont=dict(size=17),
        range=[0, 1],
        tickvals=[0, 0.2, 0.4, 0.6, 0.8, 1],
        ticktext=["0", "20", "40", "60", "80", "100"],
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(255,255,255,0.08)",
        showline=False,
    )


def _add_date_annotations(
    fig: Figure,
    *,
    x_start: datetime,
    x_end: datetime,
    midnight_points: list[datetime],
) -> None:
    def _segment_midpoint(start: datetime, end: datetime) -> datetime:
        return start + (end - start) / 2

    segment_edges = (
        [x_start] + [m for m in midnight_points if x_start < m < x_end] + [x_end]
    )

    for seg_start, seg_end in zip(segment_edges[:-1], segment_edges[1:]):
        mid = _segment_midpoint(seg_start, seg_end)

        fig.add_annotation(
            x=mid,
            y=-0.25,
            xref="x",
            yref="paper",
            text=seg_start.date().strftime("%d %b %Y"),
            showarrow=False,
            xanchor="center",
            yanchor="top",
            font=dict(size=16, color="white"),
        )


def _add_now_marker(fig: Figure, x_now: datetime) -> None:
    fig.add_vline(x=x_now, line_dash="dash", line_color="white")
    fig.add_annotation(
        x=x_now,
        xshift=-18,
        y=0.5,
        xref="x",
        yref="paper",
        text="Now",
        textangle=-90,
        showarrow=False,
        xanchor="center",
        font=dict(color="white", size=18),
    )


def _add_schedule_window_overlays(fig: Figure, spans: list[WindowSpan]) -> None:
    for span in spans:
        fig.add_vrect(
            x0=span.start,
            x1=span.end,
            fillcolor="royalblue",
            opacity=0.10,
            layer="below",
            line_width=0,
        )

        mid = span.start + (span.end - span.start) / 2
        fig.add_annotation(
            x=mid,
            y=1.19,
            xref="x",
            yref="paper",
            text="<b>Scheduled Window</b>",
            showarrow=False,
            xanchor="center",
            font=dict(color="royalblue", size=18),
        )


def _add_active_charge_overlays(fig: Figure, spans: list[ChargeSpan]) -> None:
    for span in spans:
        fill = "red" if span.is_override else "green"
        label = (
            "<b>Override Charging</b>" if span.is_override else "<b>Charging Needed</b>"
        )
        font_color = "red" if span.is_override else "green"

        fig.add_vrect(
            x0=span.start,
            x1=span.end,
            fillcolor=fill,
            opacity=0.18,
            layer="below",
            line_width=0,
        )

        mid = span.start + (span.end - span.start) / 2
        fig.add_annotation(
            x=mid,
            y=1.11,
            xref="x",
            yref="paper",
            text=label,
            showarrow=False,
            xanchor="center",
            font=dict(color=font_color, size=18),
        )


def _apply_layout(fig: Figure) -> None:
    fig.update_layout(
        margin=dict(l=8, r=8, t=80, b=95),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )


def plot_upcoming_charges(
    states: list[CombinedState], current_time: datetime
) -> Figure:
    df = _build_plot_df(states)
    fig = px.line(df, x="Time", y="State of Charge")
    fig.update_traces(mode="markers+lines")

    x_now, x_start, x_end = _get_plot_window(current_time)

    _add_hour_lines(fig, x_start, x_end)
    _add_plot_boundaries(fig, x_start, x_end)

    midnight_points = _add_midnight_lines(fig, x_start, x_end)
    tick_vals = _build_tick_values(x_now, x_start, x_end)

    _configure_axes(fig, x_start=x_start, x_end=x_end, tick_vals=tick_vals)
    _add_date_annotations(
        fig, x_start=x_start, x_end=x_end, midnight_points=midnight_points
    )
    _add_now_marker(fig, x_now)

    scheduled_spans = _compute_scheduled_window_spans(df)
    active_spans = _compute_charge_spans(df)

    _add_schedule_window_overlays(fig, scheduled_spans)
    _add_active_charge_overlays(fig, active_spans)
    _apply_layout(fig)

    return fig
