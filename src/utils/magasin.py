"""Data access for the NVE Magasinstatistikk API.

The Streamlit pages import this module instead of reading ``reservoirs.csv``.
The NVE endpoint has no date-range parameters, so the full response is cached
once and the pages materialise only the interval selected in the UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

MAGASIN_API = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

# EL/VASS have several area numbers; NO has one (0).
AREA_TYPES = ("EL", "NO", "VASS")

MEASUREMENT_COLUMNS = (
    "water_level",
    "twh_cap",
    "twh_fill",
    "water_level_prev_week",
    "water_level_change",
)

COLUMN_MAP = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "iso_year",
    "iso_uke": "iso_week",
    "fyllingsgrad": "water_level",
    "kapasitet_TWh": "twh_cap",
    "fylling_TWh": "twh_fill",
    "neste_Publiseringsdato": "next_publication_date",
    "fyllingsgrad_forrige_uke": "water_level_prev_week",
    "endring_fyllingsgrad": "water_level_change",
}

REQUIRED_COLUMNS = (
    "date",
    "area_type",
    "area_number",
    "iso_year",
    "iso_week",
    "next_publication_date",
    *MEASUREMENT_COLUMNS,
)

# Reuse the parquet cache produced by the notebook when it exists.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_CACHE = REPO_ROOT / "data" / "cache" / "magasinstatistikk.parquet"


def _coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Some pre-processing.
    Validate, type-cast and sort a Magasinstatistikk DataFrame.
    """
    
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    
    if missing:
        raise ValueError(
            "Magasinstatistikk data are missing columns: " + ", ".join(missing)
        )

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["area_type"] = frame["area_type"].astype(str)
    frame["area_number"] = frame["area_number"].astype(int)
    frame["iso_year"] = frame["iso_year"].astype(int)
    frame["iso_week"] = frame["iso_week"].astype(int)

    for column in MEASUREMENT_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    # NVE uses 0001-01-01 as a "not published yet" sentinel.
    frame["next_publication_date"] = frame["next_publication_date"].replace(
        "0001-01-01T00:00:00", pd.NA
    )
    frame["next_publication_date"] = pd.to_datetime(
        frame["next_publication_date"],
        format="%Y-%m-%dT%H:%M:%S",
        errors="coerce",
    )

    return frame.sort_values("date").reset_index(drop=True)


def _process_payload(payload: list[dict[str, Any]]) -> pd.DataFrame:
    """Rename and type-cast the NVE JSON response."""
    frame = pd.DataFrame(payload).rename(columns=COLUMN_MAP)
    return _coerce_types(frame)


def fetch_magasinstatistikk() -> pd.DataFrame:
    """Download the complete NVE history without using the Streamlit cache."""
    response = requests.get(MAGASIN_API, timeout=120)
    response.raise_for_status()
    return _process_payload(response.json())


@st.cache_data(ttl=7 * 24 * 3600, show_spinner="Loading reservoir data...")
def load_all() -> pd.DataFrame:
    """
    Return the complete Magasinstatistikk history.

    The parquet file is preferred (it is created by the P2 notebook). If it is
    missing, the API is called and the response is processed in the same way.
    """
    if PARQUET_CACHE.exists():
        return _coerce_types(pd.read_parquet(PARQUET_CACHE))

    return fetch_magasinstatistikk()


def filter_by_months(df: pd.DataFrame, months: int) -> pd.DataFrame:
    """
    Keep the first ``months`` months, starting from the first month in the data.

    The endpoint is inclusive, matching the P1 ``ReservoirData`` behaviour.
    """
    if months < 1:
        raise ValueError("months must be at least 1")
    if "date" not in df.columns:
        raise ValueError("DataFrame must contain a 'date' column")

    start = df["date"].min().to_period("M").to_timestamp()
    end = start + pd.DateOffset(months=months)
    return df.loc[(df["date"] >= start) & (df["date"] <= end)].copy()


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def load_interval(months: int) -> pd.DataFrame:
    """
    Return only the selected download interval.

    Caching is keyed on ``months``, so moving the slider gives a fast lookup
    for intervals that have already been used while still controlling how much
    data each page receives.
    """
    return filter_by_months(load_all(), months)


def area_numbers_for(df: pd.DataFrame, area_type: str) -> list[int]:
    """Return the area numbers associated with one area type."""
    values = df.loc[df["area_type"] == area_type, "area_number"].unique()
    return sorted(int(value) for value in values)
