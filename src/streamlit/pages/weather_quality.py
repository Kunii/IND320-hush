"""Weather quality page: SPC outliers and LOF anomalies in two tabs.

CRS: none. ``weather_frame`` returns an area-mean time series; the coordinates
were projected and sampled offline (EPSG:3035) — see ``docs/CA3/crs.md``.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.utils.analysis import lof_outliers, spc_outliers
from src.utils.era5_cache import build_range_frame
from src.utils.weather import (
    SOURCE_LABELS,
    WEATHER_AREAS,
    WEATHER_YEAR,
    area_points,
    available_weather_sources,
    weather_frame,
)

SOURCE_DETAIL = {
    "open-meteo": "open-meteo archive API (models=era5, elevation-corrected)",
    "cds": "Copernicus CDS ERA5 GRIB (parity mode, 1 dp per point)",
}
"""What each source is, shown under the selector."""

CDS_TERMS_URL = "https://cds.climate.copernicus.eu/licences/terms-of-use-cds"
ECMWF_NOTICE_URL = (
    "https://forum.ecmwf.int/t/data-stores-service-protection-measures-"
    "affecting-data-downloads-and-account-access-cds-ads-ewds-ecds/15481"
)
"""Where the personal-key requirement comes from."""


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
        # Precipitation cannot be negative, so a lower limit below 0 can never
        # be crossed; floor it to keep the plot honest.
        lower_bound=0.0 if column == "precipitation" else None,
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
            "limit is floored at 0, so only the upper limit can be crossed."
        )
        st.write(
            "**Why these defaults.** The cut-off is set in cycles per year, not "
            "as a fraction of coefficients, because a fraction means a different "
            "smoothing at every sampling rate: 2 % of 366 daily values is about "
            "3.5 cycles/year, 2 % of these 8 784 hourly values is about 88. "
            "**12 cycles/year is one cycle per month** — slower variation is the "
            "seasonal baseline, faster is weather. The default sits in a flat "
            "region: on this series (NO3, hourly, 2024) cut-offs of 6, 12 and 24 "
            "flag 6, 14 and 19 hours at 3σ, so the flags are not an artefact of "
            "the cut-off. **3σ is the conventional control limit** (a Shewhart "
            "chart's ±3σ band; the width here is robust, so the convention is "
            "about the width, not a normality assumption). Its sensitivity is "
            "steep and worth seeing: at 2σ this series has 469 flagged hours "
            "(5.34 %), at 2.5σ 130 (1.48 %), at 3σ 14 (0.16 %). Two sigma labels "
            "one hour in twenty; three sigma surfaces the exceptional ones. "
            "Precipitation is heavy-tailed by nature: at the same 3σ it flags "
            "602 hours (6.9 %), which is rain being rain, not a defect."
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
        st.write(
            "**Why these defaults.** **Contamination 1 %** is the task's "
            "default and it fixes the count: 1 % of 8 784 hours is 88 labels, "
            "so the number of anomalies is a choice, not a finding. **20 "
            "neighbours** is the conventional LOF setting (scikit-learn's "
            "default): small enough that the density describes a local regime, "
            "large enough that a single point cannot define its own "
            "neighbourhood. Measured on this series, 10, 20 and 50 neighbours "
            "all label 88 hours, but only 12 of those hours are shared between "
            "10 and 50 (41 between 10 and 20) — the setting chooses *which* "
            "hours count as locally unusual, not how many. That is what the "
            "slider is for: move it and watch the set change while the count "
            "stays put."
        )


def render_cds_key_panel(area_label: str) -> None:
    """Advanced: a visitor's own CDS key, used for one bounded request.

    The shipped caches make a key unnecessary. This exists so a reader can see
    the CDS path work without the author shipping a personal credential, which
    the CDS Terms of Use do not allow.
    """
    with st.expander("Advanced: bring your own CDS key"):
        st.markdown(
            "The two shipped series need no key and no download. This control "
            "fetches one month for the selected area straight from the "
            "Copernicus Climate Data Store, using **your own** free key.\n\n"
            "**Why not the author's key?** The CDS licence is personal: "
            "*\"The registration — and with it any license accepted thereunder "
            "— only applies to its named holder\"* "
            f"([CDS Terms of Use, Art. 2]({CDS_TERMS_URL})). Serving this page "
            "with one key would make that person the requestor for every "
            "visitor, from a shared cloud address — exactly the pattern "
            "ECMWF's service-protection measures are meant to stop, and those "
            "measures allow accounts to be suspended. ECMWF also asks for "
            "requests to be submitted **sequentially, not in parallel or in "
            "large batches** "
            f"([announcement, 2026-10-22]({ECMWF_NOTICE_URL})).\n\n"
            "Your key stays in this browser session, is never written to disk "
            "or logged, and is used for one request per click."
        )
        st.caption(
            "One click = one CDS request. A month is about 1 500 fields (a few "
            "MB) and the queue usually takes minutes; the series is shown as a "
            "preview, while the tabs keep analysing the shipped 2024 data."
        )

        left, right = st.columns(2)
        key = left.text_input(
            "CDS API key",
            type="password",
            key="ca3_cds_key",
            help="From your CDS profile page. Held in this session only.",
        )
        year = right.number_input(
            "Year", min_value=1990, max_value=2025, value=WEATHER_YEAR, step=1, key="ca3_cds_year"
        )

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        month = st.selectbox(
            "Month", options=list(range(1, 13)), index=0,
            format_func=lambda value: month_names[value - 1],
            key="ca3_cds_month",
        )

        if st.button(
            "Fetch this month from the CDS",
            key="ca3_cds_fetch",
            disabled=not key.strip(),
            help="Needs a CDS key above. One request, sequential by design.",
        ):
            start = pd.Timestamp(year=int(year), month=int(month), day=1)
            end = start + pd.offsets.MonthEnd(0)
            with st.spinner("Waiting for the CDS queue (usually a few minutes)..."):
                try:
                    frame = build_range_frame(
                        area_points(area_label),
                        str(start.date()),
                        str(end.date()),
                        key=key.strip(),
                    )
                except Exception as error:  # any CDS or key failure surfaces here
                    st.session_state.pop("ca3_cds_preview", None)
                    st.error(f"CDS request failed: {type(error).__name__}: {error}")
                else:
                    st.session_state["ca3_cds_preview"] = frame
                    st.success(f"Fetched {len(frame):,} hours for {start:%B %Y}.")

        preview = st.session_state.get("ca3_cds_preview")
        if isinstance(preview, pd.DataFrame) and not preview.empty:
            st.line_chart(preview.set_index("timestamp")["temperature_2m"])
            st.caption(
                f"Fetched series: {preview['timestamp'].min():%Y-%m-%d} to "
                f"{preview['timestamp'].max():%Y-%m-%d} · "
                f"{int(preview['point_count'].to_numpy().max())} cells · "
                f"mean {preview['temperature_2m'].mean():.2f} °C · "
                f"{preview['precipitation'].sum():.1f} mm"
            )
            if st.button("Clear the fetched series", key="ca3_cds_clear"):
                st.session_state.pop("ca3_cds_preview", None)
                st.rerun()


def main() -> None:
    """Render the page."""
    st.title("Weather quality")
    st.write(
        "Outlier and anomaly detection on the hourly ERA5 area means. The "
        "selector mirrors the Magasinstatistikk areas."
    )

    left, right = st.columns([3, 2])
    area_label = left.selectbox(
        "Area",
        options=list(WEATHER_AREAS),
        index=2,  # NO3 (EL 3): the area used in the notebook.
        key="ca3_weather_area",
        help="EL 1–5 map to NO1–NO5; VASS 1–3 map to East, West and North.",
    )

    sources = available_weather_sources(area_label)
    if not sources:
        st.error(f"No precomputed weather data for {area_label} ({WEATHER_YEAR}).")
        return
    # Both sources are shipped for every area; the control is only built when
    # there is a real choice, so a missing cache degrades to a caption.
    source_labels = [SOURCE_LABELS[source] for source in sources]
    if len(sources) > 1:
        chosen = right.radio(
            "Data source",
            options=source_labels,
            index=0,
            horizontal=True,
            key="ca3_weather_source",
            help=(
                "Both sources hold the same 100 land-clipped cells and the same "
                "schema. The CDS series is built in parity mode, so the analysis "
                "is the same whichever you pick."
            ),
        )
        source = sources[source_labels.index(chosen)]
    else:
        source = sources[0]
        right.caption(f"Data source: {SOURCE_LABELS[source]} (only one available)")

    try:
        weather = weather_frame(area_label, source=source)
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    points = int(pd.Series(weather["point_count"]).max())
    st.caption(
        f"{area_label} · {SOURCE_DETAIL[source]} · ERA5 {WEATHER_YEAR} · "
        f"{len(weather):,} hourly rows · "
        f"{points} land grid cells · no API calls at runtime"
    )
    if len(sources) > 1:
        st.caption(
            "The two sources agree to 0.017 K at worst and precipitation is "
            "identical (measured 2024, all eight areas), so switching cannot "
            "change the outlier or anomaly sets."
        )

    # st.tabs puts both quality checks on one page, as required by the task.
    spc_tab, lof_tab = st.tabs(["Outlier / SPC", "Anomaly / LOF"])
    with spc_tab:
        render_spc(weather)
    with lof_tab:
        render_lof(weather)

    render_cds_key_panel(area_label)

    with st.expander("Data and method"):
        st.write(
            f"The weather data are precomputed for {WEATHER_YEAR}: 100 randomly "
            "sampled locations per area, clipped to land, snapped to the 0.25° "
            "ERA5 grid and averaged per hour. The same cells are shipped from "
            "two sources — the open-meteo archive API and the Copernicus "
            "Climate Data Store — and the **Data source** control switches "
            "between them. The CDS files are built in *parity mode*: every "
            "point is rounded to one decimal before averaging, which is what "
            "the open-meteo API returns, so the two series are interchangeable "
            "(≤0.017 K; precipitation identical). Raw ERA5 would instead "
            "average unrounded values and put the annual precipitation total "
            "1.1 % high. The eight selectable areas are the five electricity "
            "price areas and the three grouped NVE precipitation regions. "
            "Whole-country `NO 0` has no weather layer, so choose an EL or "
            "VASS area. Reading a cache costs no API calls."
        )


if __name__ == "__main__":
    main()
