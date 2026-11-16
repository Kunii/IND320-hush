"""Tests for the two weather sources.

Run with::

    env -u PYTHONPATH .venv/bin/python -m pytest tests -q

No network and no CDS request: every test works on the shipped caches or on
values constructed in memory.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.utils.era5_cache import (
    build_area_cache,
    cache_name,
    parity_round,
)
from src.utils.weather import (
    SOURCE_LABELS,
    WEATHER_AREAS,
    available_weather_sources,
    weather_frame,
)


def test_parity_round_snaps_each_point_to_one_decimal():
    temperature = np.array([[0.04, 0.06], [-1.24, -1.26]])
    precipitation = np.array([[0.04, 0.06], [0.24, 0.26]])
    t, p = parity_round(temperature, precipitation)
    assert np.allclose(t, [[0.0, 0.1], [-1.2, -1.3]]), t
    assert np.allclose(p, [[0.0, 0.1], [0.2, 0.3]]), p


def test_parity_changes_the_mean_not_just_the_steps():
    """Two points that round in opposite directions move the mean."""
    raw = np.array([[0.04], [0.04]])  # mean 0.04
    rounded, _ = parity_round(raw, raw)
    assert rounded.mean() == 0.0
    assert raw.mean() != rounded.mean()


def test_cache_name_marks_the_source_and_resolution():
    hourly = cache_name("electricity", "NO3", "2024-01-01", "2024-12-31", "100", "hourly")
    daily = cache_name("electricity", "NO3", "2024-01-01", "2024-12-31", "100", "daily")
    assert hourly.endswith("_hourly_cds"), hourly
    assert daily.endswith("_daily_cds"), daily
    assert hourly != daily


def test_parity_is_rejected_for_grid_mode():
    with pytest.raises(ValueError, match="points mode"):
        build_area_cache(
            "electricity",
            "NO3",
            "2024-01-01",
            "2024-01-01",
            mode="grid",
            geometry=None,
            parity=True,
        )


def test_notebook_and_writer_agree_on_the_cds_cache_name(p3):
    """The notebook delegates CDS naming to the writer, so there is one rule."""
    import src.utils.era5_cache as era5_cache

    assert era5_cache.cache_name is cache_name
    assert p3.download_region_weather.__doc__ is not None
    assert "cds" in p3.download_region_weather.__doc__.lower()


def test_both_sources_are_shipped_for_every_area():
    for area in WEATHER_AREAS:
        sources = available_weather_sources(area)
        assert sources == ("open-meteo", "cds"), (area, sources)
        assert set(sources) <= set(SOURCE_LABELS)


def test_weather_frame_routing_and_parity():
    open_meteo = weather_frame("NO3 (EL 3)", source="open-meteo")
    cds = weather_frame("NO3 (EL 3)", source="cds")
    assert list(open_meteo.columns) == list(cds.columns)
    assert len(open_meteo) == len(cds) == 8784
    assert int(cds["point_count"].to_numpy().max()) == 100

    temp = (cds["temperature_2m"] - open_meteo["temperature_2m"]).abs()
    precip = (cds["precipitation"] - open_meteo["precipitation"]).abs()
    assert temp.max() <= 0.02, temp.max()
    # Bit-identical up to the order pandas sums the thousand point values.
    assert precip.max() <= 1e-12, precip.max()


def test_weather_frame_rejects_an_unknown_source():
    with pytest.raises(ValueError, match="Unknown weather source"):
        weather_frame("NO3 (EL 3)", source="nope")
