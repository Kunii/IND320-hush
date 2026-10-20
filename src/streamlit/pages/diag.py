"""Reservoir plot page for the IND320 P2 app."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.magasin import (
    AREA_TYPES,
    MEASUREMENT_COLUMNS,
    area_numbers_for,
    load_all,
    load_interval,
)

ALL_OPTION = "all"
AREA_PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
MEASUREMENT_DASHES = {
    "water_level": "solid",
    "twh_cap": "dash",
    "twh_fill": "dot",
    "water_level_prev_week": "dashdot",
    "water_level_change": "longdash",
}


def pretty_name(column: str) -> str:
    """Return a human-readable label for a data column."""
    return column.replace("_", " ").title()


def render_single_chart(df: pd.DataFrame, column: str) -> None:
    """Draw one measurement with one line per area number."""
    chart_df = (
        df.pivot(index="date", columns="area_number", values=column).sort_index()
    )
    chart_df.columns = [f"Area {int(area)}" for area in chart_df.columns]

    st.line_chart(
        chart_df,
        x_label="Date",
        y_label=pretty_name(column),
        height=360,
    )


def build_normalized_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Put every measurement on one 0-1 scale and return a long-format frame.

    Each measurement is min-max scaled across the selected area type and
    interval, so the columns share a comparable vertical range while the
    relative differences between area numbers within a measurement are kept.
    """
    frames: list[pd.DataFrame] = []

    for column in MEASUREMENT_COLUMNS:
        pivot = (
            df.pivot(index="date", columns="area_number", values=column)
            .sort_index()
            .astype(float)
        )

        low = pivot.min().min()
        high = pivot.max().max()
        if pd.notna(low) and pd.notna(high) and high > low:
            pivot = (pivot - low) / (high - low)
        else:
            # A constant series has no range; draw it at zero instead of NaN.
            pivot = pivot * 0.0

        pivot = pivot.clip(lower=0.0, upper=1.0)
        long_df = (
            pivot.reset_index()
            .melt(
                id_vars="date",
                var_name="area_number",
                value_name="value",
            )
            .dropna(subset=["value"])
        )
        long_df["area_number"] = long_df["area_number"].astype(int)
        long_df["measurement"] = column
        frames.append(long_df)

    return pd.concat(frames, ignore_index=True)


def render_all_chart(df: pd.DataFrame, area_numbers: list[int]) -> None:
    """
    Draw all measurements on one normalized chart.

    Colour identifies the area number and line style identifies the
    measurement. The legend therefore contains one entry per area and one per
    measurement instead of one entry per line, which keeps it inside the page.
    """
    normalized = build_normalized_data(df)

    area_colors = {
        area: AREA_PALETTE[index % len(AREA_PALETTE)]
        for index, area in enumerate(sorted(area_numbers))
    }
    fig = go.Figure()

    # Actual data traces are hidden from the legend; the dummy traces below
    # build the compact two-part legend.
    for (column, area_number), group in normalized.groupby(
        ["measurement", "area_number"], sort=False
    ):
        label = pretty_name(column)
        fig.add_trace(
            go.Scatter(
                x=group["date"],
                y=group["value"],
                mode="lines",
                name=f"{label} - Area {area_number}",
                showlegend=False,
                line={
                    "color": area_colors.get(area_number, "#777777"),
                    "dash": MEASUREMENT_DASHES.get(column, "solid"),
                    "width": 1.2,
                },
                hovertemplate=(
                    f"<b>{label} - Area {area_number}</b><br>"
                    "%{x|%Y-%m-%d}<br>"
                    "Normalized: %{y:.3f}<extra></extra>"
                ),
            )
        )

    # Legend part 1: colours represent area numbers.
    for area_number in sorted(area_numbers):
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=f"Area {area_number}",
                line={"color": area_colors[area_number], "width": 2.5},
            )
        )

    # Legend part 2: dash styles represent measurements.
    for column in MEASUREMENT_COLUMNS:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=pretty_name(column),
                line={
                    "color": "#666666",
                    "dash": MEASUREMENT_DASHES.get(column, "solid"),
                    "width": 2.5,
                },
            )
        )

    fig.update_layout(
        height=560,
        margin={"l": 10, "r": 170, "t": 10, "b": 10},
        xaxis_title="Date",
        yaxis_title="Normalized value (0-1)",
        yaxis={"range": [-0.02, 1.02]},
        legend={
            "title": {"text": "Colour = area<br>Style = measurement"},
            "orientation": "v",
            "x": 1.02,
            "xanchor": "left",
            "y": 1,
            "yanchor": "top",
            "font": {"size": 10},
        },
    )

    st.plotly_chart(fig, width="stretch")


def main() -> None:
    """Render controls and the selected reservoir chart."""
    st.title("Reservoir plot")
    st.write(
        "Select an area type and a measurement. Every area number belonging to "
        "that type is drawn as a separate line."
    )

    area_type = st.radio(
        "Area type",
        options=AREA_TYPES,
        horizontal=True,
        help="EL = Elspot areas, NO = Norway as one area, VASS = catchment areas.",
    )

    try:
        all_data = load_all()
    except Exception as exc:  # Network/API errors should be shown, not traced.
        st.error(f"Could not load the NVE data: {exc}")
        st.stop()

    total_months = int(all_data["date"].dt.to_period("M").nunique())
    months = st.slider(
        "Download interval (months from the start of the data series)",
        min_value=1,
        max_value=total_months,
        value=int(st.session_state.get("download_months", 1)),
        step=1,
        key="plot_months",
    )

    # Widget keys can be cleaned up when navigating between pages, so mirror
    # the value in an ordinary session-state entry read by the table page.
    st.session_state["download_months"] = months

    measurement = st.selectbox(
        "Measurement",
        options=[ALL_OPTION, *MEASUREMENT_COLUMNS],
        help=(
            "Choose one measurement, or plot all measurements on one chart. "
            "The 'all' view normalizes each measurement to 0-1."
        ),
    )

    try:
        df = load_interval(months)
    except Exception as exc:
        st.error(f"Could not load the selected interval: {exc}")
        st.stop()

    df = df[df["area_type"] == area_type].copy()
    if df.empty:
        st.warning("No data for this area type.")
        st.stop()

    area_numbers = area_numbers_for(df, area_type)
    st.caption(
        f"{area_type}: area numbers {', '.join(map(str, area_numbers))}. "
        f"Interval: {df['date'].min().date()} to {df['date'].max().date()} "
        f"({months} month(s))."
    )

    if measurement == ALL_OPTION:
        st.caption(
            "All measurements, normalized to 0-1 per measurement. "
            "Colour shows the area number and line style shows the measurement."
        )
        render_all_chart(df, area_numbers)
    else:
        render_single_chart(df, measurement)

    with st.expander("How the interval and normalization are handled"):
        st.write(
            "The NVE endpoint returns the full history in one response. The app "
            "downloads it once, caches the result, and then materialises only "
            "the first N months selected above. The table page reads the same "
            "session-state value, so both pages always show the same interval."
        )
        st.write(
            "When **all** is selected, every measurement is min-max scaled to "
            "0-1 across the chosen area type and interval. This makes the very "
            "different units (TWh and water level) fit on one chart without "
            "changing the shape of each series."
        )


if __name__ == "__main__":
    main()
