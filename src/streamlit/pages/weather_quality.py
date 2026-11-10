"""Weather quality page: SPC outliers and LOF anomalies in two tabs.

CRS: none. ``weather_frame`` returns an area-mean time series; the coordinates
were projected and sampled offline (EPSG:3035) — see ``docs/crs.md``.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.ca3.analysis import lof_outliers, spc_outliers
from src.ca3.data import WEATHER_AREAS, WEATHER_YEAR, weather_frame


def _top_outliers(table: pd.DataFrame, column: str, limit: int = 10) -> pd.DataFrame:
    """Return the most extreme rows of an outlier table for display."""
    display = table.assign(_abs=table[column].abs())
    display = display.sort_values("_abs", ascending=False).drop(columns="_abs")
    display = display.head(limit).reset_index()
    numeric = [column for column in display.columns if column != "timestamp"]
    display[numeric] = display[numeric].round(2)
    return display


def render_spc(weather: pd.DataFrame) -> None:
    """Render the SPC tab: series choice, DCT parameters, plot and stats."""
    st.write(
        "Statistical Process Control flags hours that depart from the slow "
        "seasonal baseline. The baseline comes from a DCT low-pass; the limits "
        "use the robust spread (MAD) of the remaining high-pass signal (SATV)."
    )

    series_label = st.radio(
        "Series",
        options=("Temperature", "Precipitation"),
        horizontal=True,
        key="ca3_spc_series",
        help="The teacher clarified that the SPC analysis should use temperature.",
    )
    if series_label == "Temperature":
        column, unit, label = "temperature_2m", "°C", "Temperature"
    else:
        column, unit, label = "precipitation", "mm/h", "Precipitation"

    left, right = st.columns(2)
    cutoff = left.slider(
        "DCT cut-off [cycles/year]",
        min_value=2,
        max_value=52,
        value=12,
        step=1,
        key="ca3_spc_cutoff",
        help="Variations slower than this are treated as the seasonal baseline. 12 ≈ one month.",
    )
    n_std = right.slider(
        "Control limits [robust σ]",
        min_value=1.5,
        max_value=5.0,
        value=3.0,
        step=0.25,
        key="ca3_spc_nstd",
        help="Width of the inlier band around the seasonal baseline.",
    )

    fig, summary, table = spc_outliers(
        pd.Series(weather[column], dtype=float),
        cutoff_per_year=cutoff,
        n_std=n_std,
        label=label,
        unit=unit,
    )
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    left, middle, right = st.columns(3)
    left.metric("Outliers", f"{summary['outliers']:,}")
    middle.metric("Share of hours", f"{summary['share']:.2%}")
    right.metric("Robust σ", f"{summary['robust_sigma']:.3f} {unit}")

    if table.empty:
        st.info("No outliers at these settings. Widen the limits or lower the cut-off.")
    else:
        st.caption("Ten most extreme outliers by absolute SATV (SATV itself is not plotted).")
        st.dataframe(
            _top_outliers(table, "satv"),
            hide_index=True,
            width="stretch",
        )

    with st.expander("How the SPC limits are built"):
        st.write(
            f"The DCT keeps the {summary['dct_coefficients_removed']} slowest "
            "coefficients as the seasonal baseline and treats the rest as the "
            "SATV. The centre is the median SATV and the width is "
            f"{n_std:g} × 1.4826 × MAD. The plotted limits are "
            "`baseline + median(SATV) ± width`; the SATV is used only to find "
            "the boundaries and the flags. For hourly precipitation the lower "
            "limit is often negative, so only the upper limit can be crossed."
        )


def render_lof(weather: pd.DataFrame) -> None:
    """Render the LOF tab: contamination/neighbours, plot and table."""
    st.write(
        "The Local Outlier Factor compares each hour with its neighbours in "
        "time. The features are the standardised time and temperature, so the "
        "method finds locally unusual spells rather than the globally most "
        "extreme values."
    )

    left, right = st.columns(2)
    contamination_pct = left.slider(
        "Expected anomaly share [%]",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.5,
        key="ca3_lof_contamination",
        help="The task's default is 1 %.",
    )
    neighbors = right.slider(
        "Neighbours",
        min_value=5,
        max_value=50,
        value=20,
        step=1,
        key="ca3_lof_neighbors",
        help="How many nearby hours define the local density.",
    )

    fig, summary, table = lof_outliers(
        pd.Series(weather["temperature_2m"], dtype=float),
        contamination=contamination_pct / 100.0,
        n_neighbors=neighbors,
    )
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    left, middle, right = st.columns(3)
    left.metric("Anomalies", f"{summary['anomalies']:,}")
    middle.metric("Share of hours", f"{summary['share']:.2%}")
    right.metric("Neighbours", f"{summary['n_neighbors']:,}")

    if table.empty:
        st.info("No anomalies at these settings.")
    else:
        display = table.head(10).reset_index().round({"value": 2, "lof_score": 2})
        st.caption("Ten highest LOF scores (higher means more unusual).")
        st.dataframe(display, hide_index=True, width="stretch")

    with st.expander("How the LOF is applied"):
        st.write(
            "Each hour is a point `(standardised time, standardised "
            "temperature)`. LOF compares the local density around that point "
            "with the density around its neighbours; the contamination "
            "parameter sets how many hours are labelled anomalous. Consecutive "
            "flagged hours usually belong to the same weather event, and an "
            "anomaly is not automatically a data error."
        )


def main() -> None:
    """Render the page."""
    st.title("Weather quality")
    st.write(
        "Outlier and anomaly detection on the hourly ERA5 area means. The "
        "selector mirrors the Magasinstatistikk areas."
    )

    area_label = st.selectbox(
        "Area",
        options=list(WEATHER_AREAS),
        index=2,  # NO3 (EL 3): the area used in the notebook.
        key="ca3_weather_area",
        help="EL 1–5 map to NO1–NO5; VASS 1–3 map to East, West and North.",
    )
    try:
        weather = weather_frame(area_label)
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    points = int(pd.Series(weather["point_count"]).max())
    st.caption(
        f"{area_label} · cached ERA5 {WEATHER_YEAR} · "
        f"{len(weather):,} hourly rows · "
        f"{points} land grid cells · no API calls at runtime"
    )

    # st.tabs puts both quality checks on one page, as required by the task.
    spc_tab, lof_tab = st.tabs(["Outlier / SPC", "Anomaly / LOF"])
    with spc_tab:
        render_spc(weather)
    with lof_tab:
        render_lof(weather)

    with st.expander("Data and method"):
        st.write(
            f"The weather data are precomputed from open-meteo ERA5 for "
            f"{WEATHER_YEAR}: 100 randomly sampled locations per area, clipped "
            "to land, snapped to the 0.25° ERA5 grid and averaged per hour. "
            "The eight selectable areas are the five electricity price areas "
            "and the three grouped NVE precipitation regions. Whole-country "
            "`NO 0` has no weather layer, so choose an EL or VASS area. "
            "Reading the cache costs no API calls."
        )


if __name__ == "__main__":
    main()
