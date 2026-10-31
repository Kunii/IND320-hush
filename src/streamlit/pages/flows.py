"""Cross-border flow page for the IND320 P2 app."""

from __future__ import annotations

import calendar

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils.mongo import get_borders, get_flows, get_pie_totals, get_years

DIRECTIONS = ("Export", "Import")
PIE_COLORS = {"Export": "#2a9d8f", "Import": "#e76f51"}
LINE_COLORS = {"Export": "#1f77b4", "Import": "#9ecae1"}
MONTH_OPTIONS = tuple(range(1, 13))


def latest_complete_year(years: list[int]) -> int:
    """Return the most recent year that is not the current (partial) year."""
    current_year = pd.Timestamp.now().year
    complete_years = [year for year in years if year < current_year]
    return max(complete_years) if complete_years else max(years)


def render_pie(connection: str, year: int) -> None:
    """Render the yearly export/import pie for one connection."""
    pie_df = get_pie_totals(connection, year)
    if pie_df.empty:
        st.info("No data for this connection and year.")
        return

    total = pie_df["twh"].sum()
    fig = go.Figure(
        go.Pie(
            labels=pie_df["direction"],
            values=pie_df["twh"],
            marker={
                "colors": [
                    PIE_COLORS.get(direction, "#999999")
                    for direction in pie_df["direction"]
                ]
            },
            textinfo="label+percent",
            customdata=pie_df["twh"],
            hovertemplate=(
                "<b>%{label}</b><br>%{customdata:.3f} TWh<extra></extra>"
            ),
            sort=False,
        )
    )
    fig.update_layout(
        title=f"{connection} - {year} (total {total:.2f} TWh)",
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=420,
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch")


def render_line_chart(
    connection: str, year: int, months: list[int] | tuple[int, ...] | None
) -> None:
    """Render the monthly flow profile for the selected months."""
    if not months:
        st.info("Select at least one month.")
        return

    flows = get_flows(connection, year, tuple(sorted(months)))
    if flows.empty:
        st.info("No flow data for this selection.")
        return

    # One trace per month and direction. Splitting by month prevents a
    # misleading straight line across months that were not selected.
    fig = go.Figure()
    for direction in DIRECTIONS:
        first_trace = True
        for month in sorted(months):
            month_df = flows[
                (flows["direction"] == direction)
                & (flows["timestamp"].dt.month == month)
            ]
            if month_df.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=month_df["timestamp"],
                    y=month_df["quantity"],
                    mode="lines",
                    name=direction,
                    legendgroup=direction,
                    showlegend=first_trace,
                    line={
                        "color": LINE_COLORS.get(direction, "#777777"),
                        "width": 1.2,
                    },
                )
            )
            first_trace = False

    fig.update_layout(
        xaxis_title="Timestamp (UTC)",
        yaxis_title="Power (MW)",
        height=420,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01},
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"{connection}, {year}: "
        f"{', '.join(calendar.month_abbr[m] for m in sorted(months))}. "
        f"{len(flows):,} observations."
    )


def render_source_expander(connection: str, year_count: int) -> None:
    """Document where the cross-border data come from and how they are stored."""
    with st.expander("Data source and processing"):
        st.markdown(
            f"""
            **Source:** ENTSO-E Transparency Platform, *Cross-border physical
            flows* (document type `A11`, business type `A66`).
            """
        )


def main() -> None:
    """Render the two-column cross-border flow view."""
    st.title("Cross-border flows")
    st.write(
        "Physical flows between Norway and its neighbouring areas, stored in "
        "MongoDB after being fetched from the ENTSO-E Transparency Platform."
    )

    try:
        borders = get_borders()
    except Exception as exc:  # Connection problems should be readable in the UI.
        st.error(
            "Could not connect to MongoDB. Check the `mongo_db` secrets locally "
            f"and in Streamlit Cloud. Details: {exc}"
        )
        st.stop()

    if not borders:
        st.warning("The MongoDB collection is empty. Run the P2 notebook first.")
        st.stop()

    left, right = st.columns(2)

    with left:
        st.subheader("Yearly total")
        connection = st.radio(
            "Connection",
            options=borders,
            help="Neighbouring country connected to Norway.",
        )

        try:
            years = get_years(connection)
        except Exception as exc:
            st.error(f"Could not read the years for {connection}: {exc}")
            st.stop()

        if not years:
            st.warning("No years available for this connection.")
            st.stop()

        default_year = latest_complete_year(years)
        year = st.selectbox(
            "Year",
            options=years,
            index=years.index(default_year),
        )
        render_pie(connection, year)

    with right:
        st.subheader("Monthly profile")
        months = st.pills(
            "Months to include",
            options=list(MONTH_OPTIONS),
            selection_mode="multi",
            default=[1],
            format_func=lambda month: calendar.month_abbr[month],
            help="Select any set of months. The chart concatenates the chosen months.",
            width="stretch",
            wrap=True,
        )
        render_line_chart(connection, year, months)

    render_source_expander(connection, len(years))


if __name__ == "__main__":
    main()
