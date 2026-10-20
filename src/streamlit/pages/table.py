"""Reservoir table page for the IND320 P2 app."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.magasin import (
    AREA_TYPES,
    MEASUREMENT_COLUMNS,
    area_numbers_for,
    load_interval,
)

TIDY_COLUMNS = [
    "date",
    "area_type",
    "area_number",
    "water_level",
    "twh_cap",
    "twh_fill",
    "water_level_prev_week",
    "water_level_change",
]


def build_sparkline_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build one row per area number and measurement.

    ``st.column_config.LineChartColumn`` expects a plain list of values per
    row, so the time series is stored in the ``Series`` column.
    """
    rows: list[dict[str, object]] = []

    for area_number, area_df in df.groupby("area_number", sort=True):
        area_df = area_df.sort_values("date")
        for column in MEASUREMENT_COLUMNS:
            series = area_df[column].dropna()
            if series.empty:
                continue

            rows.append(
                {
                    "Area": f"Area {int(area_number)}",
                    "Measurement": column,
                    "Min": float(series.min()),
                    "Max": float(series.max()),
                    "Series": series.tolist(),
                }
            )

    return pd.DataFrame(rows)


def render_table(df: pd.DataFrame, area_type: str, months: int) -> None:
    """Render the sparkline table and the optional tidy-data expander."""
    area_numbers = area_numbers_for(df, area_type)

    st.caption(
        f"Showing the first **{months}** month(s) of the data "
        f"({df['date'].min().date()} to {df['date'].max().date()}). "
        "Change the interval on the **Reservoir plot** page."
    )

    st.subheader(f"{area_type} area numbers: {', '.join(map(str, area_numbers))}")
    st.dataframe(
        build_sparkline_table(df),
        hide_index=True,
        width="stretch",
        height=600,
        column_config={
            "Area": st.column_config.TextColumn("Area"),
            "Measurement": st.column_config.TextColumn("Measurement"),
            "Min": st.column_config.NumberColumn("Min", format="%.3f"),
            "Max": st.column_config.NumberColumn("Max", format="%.3f"),
            "Series": st.column_config.LineChartColumn(
                "Selected interval",
                help=(
                    "Line chart of the measurement over the selected download "
                    "interval."
                ),
            ),
        },
    )

    with st.expander("Show the tidy data table"):
        st.dataframe(
            df[TIDY_COLUMNS].tail(500),
            hide_index=True,
            width="stretch",
        )


def main() -> None:
    """Load the selected interval and render the table page."""
    st.title("Reservoir table")
    st.write(
        "The table below is built from the NVE Magasinstatistikk API. Each row "
        "is one measurement for one area number, and the last column contains "
        "the time series for the selected download interval."
    )

    # The slider lives on the Reservoir plot page. `download_months` is a plain
    # session-state value (not a widget key), so it survives page navigation.
    months = int(st.session_state.get("download_months", 1))

    area_type = st.radio(
        "Area type",
        options=AREA_TYPES,
        horizontal=True,
        help="EL = Elspot areas, NO = Norway as one area, VASS = catchment areas.",
    )

    try:
        df = load_interval(months)
    except Exception as exc:  # Network/API errors should be shown, not traced.
        st.error(f"Could not load the NVE data: {exc}")
        st.stop()

    df = df[df["area_type"] == area_type].copy()
    if df.empty:
        st.warning("No data for this area type.")
        st.stop()

    render_table(df, area_type, months)


if __name__ == "__main__":
    main()
