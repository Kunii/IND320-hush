"""Data access for the CA3 pages.

The reservoir series comes from the cached Magasinstatistikk parquet (through
``src.utils.magasin``). The weather series comes from the precomputed ERA5
parquet files in ``data/precomputed/weather``, so the deployed app makes no
open-meteo calls at runtime.

CRS: none. Nothing in this module touches coordinates — the shapes were
projected and sampled once by ``notebooks/CA3/precompute_weather.py`` (EPSG:3035,
equal-area), and what reaches the app is an area-keyed time series. That is
deliberate: no geometry, no projection, nothing to get wrong at request time.
``docs/crs.md`` explains which CRS is used where.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils.magasin import load_all

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMPUTED_WEATHER = REPO_ROOT / "data" / "precomputed" / "weather"
WEATHER_YEAR = 2024

# The app selectors use the Magasinstatistikk names; each maps to the NVE layer
# kind and area name used by the precompute script.
WEATHER_AREAS: dict[str, tuple[str, str]] = {
    "NO1 (EL 1)": ("electricity", "NO1"),
    "NO2 (EL 2)": ("electricity", "NO2"),
    "NO3 (EL 3)": ("electricity", "NO3"),
    "NO4 (EL 4)": ("electricity", "NO4"),
    "NO5 (EL 5)": ("electricity", "NO5"),
    "East (VASS 1)": ("precipitation", "East"),
    "West (VASS 2)": ("precipitation", "West"),
    "North (VASS 3)": ("precipitation", "North"),
}


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def filling_series(area_type: str, area_number: int) -> pd.Series:
    """Return the weekly filling series for one Magasinstatistikk area."""
    frame = load_all()
    subset = frame.loc[
        (frame["area_type"] == area_type)
        & (frame["area_number"] == int(area_number))
    ]
    if subset.empty:
        raise ValueError(f"No filling data for {area_type} {area_number}")

    series = subset.set_index("date")["water_level"].sort_index()
    # Make the index regular: STL and the spectrogram need evenly spaced weeks.
    series = series.asfreq("7D").interpolate()
    series.name = f"{area_type} {area_number}"
    return series


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def weather_frame(area_label: str, year: int = WEATHER_YEAR) -> pd.DataFrame:
    """Load the precomputed hourly ERA5 area mean for one selector label."""
    if area_label not in WEATHER_AREAS:
        raise KeyError(f"Unknown weather area {area_label!r}")
    kind, name = WEATHER_AREAS[area_label]

    pattern = f"weather_{kind}_{name}_{year}-01-01_{year}-12-31_*_hourly.parquet"
    matches = sorted(PRECOMPUTED_WEATHER.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No precomputed weather cache for {area_label} ({year}). "
            "Run notebooks/CA3/precompute_weather.py first."
        )

    frame = pd.read_parquet(matches[0])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame.set_index("timestamp").sort_index()
