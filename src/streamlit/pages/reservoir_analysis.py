"""Reservoir analysis page: STL decomposition and spectrogram in two tabs.

CRS: none. The filling series is keyed by area, not by coordinate — see
``docs/crs.md``.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.ca3.analysis import spectrogram_analysis, stl_analysis
from src.ca3.data import filling_series
from src.utils.magasin import AREA_TYPES, area_numbers_for, load_all


def render_area_selector() -> tuple[str, int]:
    """Local selector: the P2 pages do not share an area-number selection."""
    area_type = st.radio(
        "Area type",
        options=AREA_TYPES,
        horizontal=True,
        key="ca3_analysis_area_type",
        help="EL = price areas, NO = Norway as one area, VASS = reservoir regions.",
    )
    numbers = area_numbers_for(load_all(), area_type)
    area_number = st.selectbox(
        "Area",
        options=numbers,
        format_func=lambda value: f"Area {int(value)}",
        key=f"ca3_analysis_area_number_{area_type}",
    )
    return area_type, int(area_number)


def render_stl(series) -> None:
    """Render the STL tab: parameters, decomposition and a short summary."""
    st.write(
        "STL splits the weekly filling series into a slowly varying trend, a "
        "repeating annual cycle and the residual."
    )
    left, middle, right = st.columns(3)
    seasonal = left.slider(
        "Seasonal smoother [weeks]",
        min_value=7,
        max_value=51,
        value=13,
        step=2,
        help="Odd window for the seasonal LOESS smoother (default 13).",
    )
    trend = middle.slider(
        "Trend smoother [weeks]",
        min_value=53,
        max_value=301,
        value=101,
        step=2,
        help="Odd window for the trend smoother; must exceed the 52-week period.",
    )
    robust = right.checkbox(
        "Robust fitting",
        value=True,
        help="Down-weights unusual weeks so they do not pull the trend.",
    )

    try:
        fig, result = stl_analysis(
            series, seasonal=seasonal, trend=trend, robust=robust
        )
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    except ValueError as error:
        st.error(f"STL could not run with these parameters: {error}")
        return

    left, middle, right = st.columns(3)
    left.metric(
        "Trend range",
        f"{result.trend.min():.2f} – {result.trend.max():.2f}",
        help="Minimum and maximum of the fitted trend (filling fraction).",
    )
    middle.metric(
        "Seasonal amplitude",
        f"{result.seasonal.max() - result.seasonal.min():.2f}",
        help="Peak-to-peak size of the fitted annual cycle.",
    )
    right.metric(
        "Residual std",
        f"{result.resid.std():.3f}",
        help="Spread left after removing trend and season.",
    )

    with st.expander("What the parameters do"):
        st.write(
            "The **seasonal** smoother controls how quickly the annual pattern "
            "may change between years; the **trend** smoother controls how "
            "smooth the long-term level is. Both must be odd, and the trend "
            "window must be longer than the 52-week period. **Robust** fitting "
            "reduces the influence of exceptional weeks such as drought years."
        )


def render_spectrogram(series) -> None:
    """Render the spectrogram tab: window/overlap controls and the plot."""
    st.write(
        "The spectrogram shows how the strength of each frequency changes over "
        "time. Frequency is measured in cycles per week."
    )
    left, right = st.columns(2)
    window = left.slider(
        "Window length [weeks]",
        min_value=26,
        max_value=260,
        value=52,
        step=26,
        help="One year (52 weeks) is the shortest window that resolves an annual cycle.",
    )
    # The key includes the window so the default overlap resets when the
    # window shrinks and the old value would be invalid.
    overlap = right.slider(
        "Window overlap [weeks]",
        min_value=0,
        max_value=window - 1,
        value=min(window - 1, window // 2),
        step=1,
        key=f"ca3_spectrogram_overlap_{window}",
        help="Samples shared by neighbouring windows; more overlap gives smoother time resolution.",
    )

    try:
        fig, frequencies, times, power = spectrogram_analysis(
            series, window=window, overlap=overlap
        )
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    except ValueError as error:
        st.error(f"The spectrogram could not be computed: {error}")
        return

    left, middle, right = st.columns(3)
    left.metric("Segments", f"{len(times):,}")
    middle.metric(
        "Frequency resolution",
        f"{frequencies[1] - frequencies[0]:.4f} cycles/week",
    )
    right.metric(
        "Annual cycle",
        "0.0192 cycles/week",
        help="1/52: where the yearly draw-down and refill appears.",
    )

    with st.expander("How to read the spectrogram"):
        st.write(
            "Bright colours mean strong variation at that frequency and time. "
            "The persistent band near **0.019 cycles/week** is the annual "
            "cycle; weaker bands above it are harmonics because the reservoir "
            "fills faster than it is drawn down. A longer window sharpens the "
            "frequency axis; a shorter window sharpens the time axis."
        )


def main() -> None:
    """Render the page."""
    st.title("Reservoir analysis")
    st.write(
        "STL decomposition and spectrogram of the weekly reservoir filling "
        "series from NVE Magasinstatistikk."
    )

    area_type, area_number = render_area_selector()
    try:
        series = filling_series(area_type, area_number)
    except Exception as error:  # API/cache errors should be shown, not traced.
        st.error(f"Could not load the filling series: {error}")
        st.stop()

    st.caption(
        f"{area_type} {area_number}: {len(series):,} weekly observations. "
        "Filling is the NVE `fyllingsgrad` fraction."
    )

    # st.tabs keeps both analyses on one page, as required by the task.
    stl_tab, spectrogram_tab = st.tabs(["STL", "Spectrogram"])
    with stl_tab:
        render_stl(series)
    with spectrogram_tab:
        render_spectrogram(series)


if __name__ == "__main__":
    main()
