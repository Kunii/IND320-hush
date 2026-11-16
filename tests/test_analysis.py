"""Tests for the CA3 analysis helpers and the notebook's data functions.

Run with::

    env -u PYTHONPATH .venv/bin/python -m pytest tests -q

The helpers defined in ``Proj-P3.py`` are reached through the ``p3`` fixture in
``conftest.py``, which skips the notebook's tagged run cells. No network is
used: every series is synthetic or read from the shipped caches.

The last four tests are property tests: they assert a behaviour (limit centre,
scale invariance, a known frequency, robust STL) rather than one run's numbers.
"""

from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from src.utils.analysis import (
    lof_outliers,
    robust_sigma,
    satv_from_dct,
    spectrogram_analysis,
    spc_outliers,
    stl_analysis,
)

NVE_REGION = "data/shapefiles/atlas_nve/NVE_Region/NVE_Region.shp"


def synthetic_filling(periods: int = 260, seed: int = 0) -> pd.Series:
    """Return a regular weekly series with a yearly cycle and noise."""
    index = pd.date_range("2020-01-06", periods=periods, freq="W-MON")
    values = (
        60
        + 10 * np.sin(2 * np.pi * np.arange(periods) / 52)
        + np.random.default_rng(seed).normal(0, 2, periods)
    )
    return pd.Series(values, index=index, name="test_filling")


def synthetic_daily(periods: int = 366) -> pd.Series:
    """Return a daily series with a yearly cycle."""
    index = pd.date_range("2024-01-01", periods=periods, freq="D")
    values = 10 * np.sin(2 * np.pi * np.arange(periods) / periods)
    return pd.Series(values, index=index, name="test_daily")


def test_robust_sigma_scales_mad():
    values = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    expected = 1.4826 * np.median(np.abs(values - np.median(values)))
    assert np.isclose(robust_sigma(values), expected)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("NO 3", "NO3"), (" no3 ", "NO3"), ("RØ", "RØ")],
)
def test_normalise_code(p3, raw, expected):
    assert p3.normalise_code(raw) == expected


@pytest.mark.parametrize(
    ("region", "kind"),
    [("NO3", "electricity"), ("NO 3", "electricity"), ("East", "precipitation")],
)
def test_region_kind(p3, region, kind):
    assert p3.region_kind(region) == kind


def test_region_kind_rejects_unknown(p3):
    with pytest.raises(KeyError):
        p3.region_kind("nope")


def test_area_codes(p3):
    assert p3.area_codes("electricity")["NO1"] == ("NO1",)
    assert p3.area_codes("precipitation")["East"] == ("RS", "RØ")


def test_select_area_geometry_rejects_missing_code(p3):
    """A group code that is absent must raise, not silently shrink the area."""
    from shapely.geometry import box

    frame = gpd.GeoDataFrame(
        {"REGION": ["RS", "RV"], "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)]},
        crs="EPSG:4326",
    )
    with pytest.raises(KeyError, match="RØ"):
        p3.select_area_geometry(frame, "precipitation", "East")


def test_select_area_geometry_rejects_mojibake_code(p3):
    """The latin-1 misread of NVE_Region must fail loudly, not drop Region Øst."""
    from shapely.geometry import box

    frame = gpd.GeoDataFrame(
        {"REGION": ["RS", "RÃ\x98"], "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)]},
        crs="EPSG:4326",
    )
    with pytest.raises(KeyError):
        p3.select_area_geometry(frame, "precipitation", "East")


def test_official_shapefile_reads_all_region_codes(p3):
    """The downloaded NVE_Region.shp must expose RØ as UTF-8, not 'RÃ˜'."""
    path = p3.REPO_ROOT / NVE_REGION
    if not path.exists():
        pytest.skip("official NVE_Region.shp not present")
    frame = p3.read_area_shapefile(path)
    assert set(frame["REGION"]) == {"RS", "RV", "RØ", "RM", "RN"}


def test_east_group_covers_south_and_east(p3):
    """Regression: East is RS + RØ, about 138 366 km2, not RS alone.

    The comparison is made in EPSG:25833 — the source CRS, in metres — because
    the geometry is stored as EPSG:4326 here and an area in square degrees is
    meaningless. 25833 inflates by ~0.2 % against equal-area EPSG:3035, which is
    why the tolerance is 100 km² and not 1.
    """
    path = p3.REPO_ROOT / NVE_REGION
    if not path.exists():
        pytest.skip("official NVE_Region.shp not present")
    frame = p3.read_area_shapefile(path)
    east = p3.select_area_geometry(frame, "precipitation", "East")
    area = gpd.GeoSeries([east], crs="EPSG:4326").to_crs(25833).area.iloc[0] / 1e6
    assert abs(area - 138_366) < 100, f"East area is {area:,.0f} km2"


def test_weather_cache_name_includes_count(p3):
    first = p3.weather_cache_name("electricity", "NO3", "2024-01-01", "2024-12-31", 24)
    second = p3.weather_cache_name(
        "electricity", "NO3", "2024-01-01", "2024-12-31", 1000
    )
    assert first != second


def test_download_region_weather_rejects_bad_interval(p3):
    with pytest.raises(ValueError):
        p3.download_region_weather("NO3", "2024-12-31", "2024-01-01", count=1)


def test_filling_series_is_regular(p3):
    index = pd.date_range("2024-01-01", periods=10, freq="W-MON")
    frame = pd.DataFrame(
        {
            "date": index,
            "area_type": "NO",
            "area_number": 0,
            "iso_year": index.isocalendar().year,
            "iso_week": index.isocalendar().week,
            "water_level": np.linspace(0.4, 0.6, len(index)),
            "twh_cap": 1.0,
            "twh_fill": 0.5,
            "water_level_prev_week": 0.5,
            "water_level_change": 0.01,
            "next_publication_date": pd.NaT,
        }
    )
    series = p3.filling_series(frame)
    assert not series.isna().any()
    assert len(series) == len(index)
    assert series.index.to_series().diff().dropna().unique().tolist() == [
        pd.Timedelta(days=7)
    ]


def test_area_mean_aggregates_locations(p3):
    weather = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]
            ),
            "lat": [60.0, 61.0, 60.0, 61.0],
            "lon": [10.0, 9.0, 10.0, 9.0],
            "temperature_2m": [0.0, 4.0, 2.0, 6.0],
            "precipitation": [1.0, 3.0, 0.0, 2.0],
        }
    )
    daily = p3.area_mean(weather)
    assert daily.loc["2024-01-01", "temperature_2m"] == 2.0
    assert daily.loc["2024-01-01", "precipitation"] == 2.0
    assert daily.loc["2024-01-01", "point_count"] == 2


def test_stl_decomposition_reconstructs_series():
    series = synthetic_filling()
    fig, result = stl_analysis(series)
    reconstructed = result.trend + result.seasonal + result.resid
    assert np.allclose(reconstructed, series.to_numpy(), atol=1e-8)
    plt.close(fig)


def test_stl_rejects_even_seasonal():
    with pytest.raises(ValueError):
        stl_analysis(synthetic_filling(), seasonal=12)


def test_spectrogram_shapes():
    fig, frequencies, times, power = spectrogram_analysis(synthetic_filling())
    assert power.shape == (frequencies.size, times.size)
    assert np.all(power >= 0)
    plt.close(fig)


def test_satv_removes_constant_signal():
    index = pd.date_range("2024-01-01", periods=366, freq="D")
    series = pd.Series(5.0, index=index, name="constant")
    satv = satv_from_dct(series, cutoff_fraction=0.02)
    assert np.allclose(satv, 0.0, atol=1e-10)


def test_satv_removes_annual_cycle():
    series = synthetic_daily()
    satv = satv_from_dct(series, cutoff_fraction=0.02)
    assert np.std(satv) < 0.5 * np.std(series.to_numpy())


def test_spc_flags_injected_spike():
    index = pd.date_range("2024-01-01", periods=366, freq="D")
    values = np.random.default_rng(0).normal(0, 1, 366)
    values[100] += 15
    series = pd.Series(values, index=index, name="spike")
    fig, summary, outliers = spc_outliers(series, cutoff_per_year=12, n_std=3.0)
    assert index[100] in outliers.index
    assert set(outliers.columns) == {"value", "satv", "lower", "upper"}
    plt.close(fig)


def test_lof_flags_about_contamination():
    index = pd.date_range("2024-01-01", periods=200, freq="D")
    values = np.random.default_rng(1).normal(0, 1, 200)
    series = pd.Series(values, index=index, name="lof")
    fig, summary, outliers = lof_outliers(series, contamination=0.05)
    assert 8 <= len(outliers) <= 12
    assert set(outliers.columns) == {"value", "lof_score"}
    plt.close(fig)


def test_spc_limit_centre_tracks_slow_component():
    """The limit centre must follow the slow DCT component, not the fast one."""
    n = 366
    index = pd.date_range("2024-01-01", periods=n, freq="D")
    x = np.pi * (np.arange(n) + 0.5) / n
    slow = 3 + 0.6 * np.cos(2 * x)
    fast = 0.1 * np.cos(100 * x)
    series = pd.Series(slow + fast, index=index, name="dct")
    fig, summary, table = spc_outliers(series, cutoff_per_year=2, n_std=3.0)
    centre = (
        np.asarray(fig.axes[0].lines[2].get_ydata(), dtype=float)
        + np.asarray(fig.axes[0].lines[3].get_ydata(), dtype=float)
    ) / 2
    assert np.allclose(centre, slow, atol=0.01)
    plt.close(fig)


def test_lof_is_scale_invariant():
    """Changing the temperature unit must not change which points are anomalous."""
    n = 200
    index = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(42)
    values = 10 + np.sin(2 * np.pi * np.arange(n) / 7) + rng.normal(0, 0.05, n)
    series = pd.Series(values, index=index, name="temperature")
    series.loc[index[50]] += 8
    series.loc[index[120]] -= 8
    fig_c, _, anomalies_c = lof_outliers(series, contamination=0.01)
    fig_f, _, anomalies_f = lof_outliers(series * 1.8 + 32, contamination=0.01)
    assert set(anomalies_c.index) == set(anomalies_f.index)
    plt.close(fig_c)
    plt.close(fig_f)


def test_spectrogram_known_frequency_shift():
    """A 52-week cycle must become a 13-week cycle in the second half."""
    n = 20 * 52
    index = pd.date_range("2000-01-02", periods=n, freq="W-SUN")
    t = np.arange(n)
    values = 0.5 + 0.15 * np.where(
        t < n // 2, np.sin(2 * np.pi * t / 52), np.sin(2 * np.pi * t / 13)
    )
    fig, frequencies, times, power = spectrogram_analysis(
        pd.Series(values, index=index, name="chirp"),
        window=52,
        overlap=26,
        max_frequency=None,
    )
    first = frequencies[np.argmax(power[:, 0])]
    last = frequencies[np.argmax(power[:, -1])]
    assert np.isclose(first, 1 / 52)
    assert np.isclose(last, 1 / 13)
    plt.close(fig)


def test_stl_robust_reduces_spike_influence():
    """Robust STL must keep the trend closer to the known trend at a spike."""
    n = 6 * 52
    index = pd.date_range("2018-01-07", periods=n, freq="W-SUN")
    t = np.arange(n)
    known_trend = 0.5 + 0.0002 * t
    known_season = 0.15 * np.sin(2 * np.pi * t / 52)
    rng = np.random.default_rng(42)
    values = known_trend + known_season + rng.normal(0, 0.005, n)
    spike = n // 2 + 26
    values[spike] += 0.30
    series = pd.Series(values, index=index, name="spike")
    fig_robust, robust = stl_analysis(series, robust=True)
    fig_plain, plain = stl_analysis(series, robust=False)
    robust_error = abs(robust.trend[spike] - known_trend[spike])
    plain_error = abs(plain.trend[spike] - known_trend[spike])
    assert robust_error < plain_error
    plt.close(fig_robust)
    plt.close(fig_plain)
