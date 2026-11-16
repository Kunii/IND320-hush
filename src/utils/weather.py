"""Data access for the precomputed ERA5 weather series.

The series comes from the parquet files in ``data/precomputed/weather``, so the
deployed app makes no API calls at runtime. The reservoir series and the
Magasinstatistikk API live in ``src.utils.magasin``; the four analysis helpers
(STL, spectrogram, SPC, LOF) live in ``src.utils.analysis``.

Two sources are shipped for the same eight areas and the same 100 land-clipped
cells: the open-meteo archive API and the Copernicus CDS. The CDS files are
built in parity mode (each point rounded to one decimal before averaging), so
the two series agree to 0.017 K and precipitation is identical; the page can
switch between them without changing the analysis.

CRS: none. Nothing in this module touches coordinates — the shapes were
projected and sampled once by ``notebooks/CA3/precompute_weather.py`` (EPSG:3035,
equal-area), and what reaches the app is an area-keyed time series. That is
deliberate: no geometry, no projection, nothing to get wrong at request time.
``docs/CA3/crs.md`` explains which CRS is used where.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMPUTED_WEATHER = REPO_ROOT / "data" / "precomputed" / "weather"
WEATHER_YEAR = 2024

WEATHER_SOURCES: dict[str, str] = {"open-meteo": "", "cds": "_cds"}
"""Source key → file-name suffix. The CDS caches carry ``_cds`` so they never
collide with an open-meteo file, and the open-meteo glob cannot match them."""

SOURCE_LABELS: dict[str, str] = {"open-meteo": "Open-Meteo", "cds": "Copernicus CDS"}
"""Display names for the page's source control."""

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
def weather_frame(
    area_label: str,
    year: int = WEATHER_YEAR,
    source: str = "open-meteo",
) -> pd.DataFrame:
    """Load the precomputed hourly ERA5 area mean for one selector label.

    ``source`` selects the producing source: ``"open-meteo"`` (archive API) or
    ``"cds"`` (Copernicus CDS, parity mode). Both hold the same 100 cells and
    the same schema, so the analysis is source-independent.
    """
    if area_label not in WEATHER_AREAS:
        raise KeyError(f"Unknown weather area {area_label!r}")
    if source not in WEATHER_SOURCES:
        raise ValueError(f"Unknown weather source {source!r}; use {list(WEATHER_SOURCES)}")
    kind, name = WEATHER_AREAS[area_label]

    pattern = (
        f"weather_{kind}_{name}_{year}-01-01_{year}-12-31_*_hourly"
        f"{WEATHER_SOURCES[source]}.parquet"
    )
    matches = sorted(PRECOMPUTED_WEATHER.glob(pattern))
    if not matches:
        available = available_weather_sources(area_label, year)
        raise FileNotFoundError(
            f"No {source} precomputed weather cache for {area_label} ({year}). "
            f"Available sources: {', '.join(available) or 'none'}. "
            "Run notebooks/CA3/precompute_weather.py for open-meteo, or "
            "build_area_cache(..., parity=True, output_dir=PRECOMPUTED_WEATHER) "
            "for CDS."
        )

    frame = pd.read_parquet(matches[0])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame.set_index("timestamp").sort_index()


def area_points(area_label: str) -> pd.DataFrame:
    """The sampled cells for one area, shipped beside the caches.

    Needed by the app's bring-your-own-key path: the precomputed parquet holds
    an area mean with no coordinates, so a fresh CDS request needs the same
    cells the cache was built from.
    """
    if area_label not in WEATHER_AREAS:
        raise KeyError(f"Unknown weather area {area_label!r}")
    kind, name = WEATHER_AREAS[area_label]
    path = PRECOMPUTED_WEATHER / f"points_{kind}_{name}_c100_land3035.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing sampled cells for {area_label}: {path.name}")
    return pd.read_parquet(path)


def available_weather_sources(area_label: str, year: int = WEATHER_YEAR) -> tuple[str, ...]:
    """Sources that actually have a cache for this area and year."""
    if area_label not in WEATHER_AREAS:
        raise KeyError(f"Unknown weather area {area_label!r}")
    kind, name = WEATHER_AREAS[area_label]
    found = []
    for source, suffix in WEATHER_SOURCES.items():
        pattern = f"weather_{kind}_{name}_{year}-01-01_{year}-12-31_*_hourly{suffix}.parquet"
        if any(PRECOMPUTED_WEATHER.glob(pattern)):
            found.append(source)
    return tuple(found)
