"""Self-tests for the CA3 analysis helpers.

Run with:

    .venv/bin/python notebooks/CA3/test_proj_p3.py

The functions are named ``test_*`` so pytest can also collect them, but the
plain runner keeps the hand-in independent of extra test dependencies.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).with_name("Proj-P3.py")


def load_analysis_module():
    """Import ``Proj-P3.py`` despite the hyphen in its filename."""
    spec = importlib.util.spec_from_file_location("proj_p3", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["proj_p3"] = module
    spec.loader.exec_module(module)
    return module


p3 = load_analysis_module()


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
    assert np.isclose(p3.robust_sigma(values), expected)


def test_normalise_code():
    assert p3.normalise_code("NO 3") == "NO3"
    assert p3.normalise_code(" no3 ") == "NO3"
    assert p3.normalise_code("RØ") == "RØ"


def test_region_kind():
    assert p3.region_kind("NO3") == "electricity"
    assert p3.region_kind("NO 3") == "electricity"
    assert p3.region_kind("East") == "precipitation"
    try:
        p3.region_kind("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown region should raise KeyError")


def test_area_codes():
    assert p3.area_codes("electricity")["NO1"] == ("NO1",)
    assert p3.area_codes("precipitation")["East"] == ("RS", "RØ")


def test_select_area_geometry_rejects_missing_code():
    """A group code that is absent must raise, not silently shrink the area."""
    from shapely.geometry import box

    frame = gpd.GeoDataFrame(
        {"REGION": ["RS", "RV"], "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)]},
        crs="EPSG:4326",
    )
    try:
        p3.select_area_geometry(frame, "precipitation", "East")
    except KeyError as error:
        assert "RØ" in str(error)
    else:
        raise AssertionError("a missing RØ row should raise KeyError")


def test_select_area_geometry_rejects_mojibake_code():
    """The latin-1 misread of NVE_Region must fail loudly, not drop Region Øst."""
    from shapely.geometry import box

    frame = gpd.GeoDataFrame(
        {"REGION": ["RS", "RÃ\x98"], "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)]},
        crs="EPSG:4326",
    )
    try:
        p3.select_area_geometry(frame, "precipitation", "East")
    except KeyError:
        pass
    else:
        raise AssertionError("mojibake REGION codes should raise KeyError")


def test_official_shapefile_reads_all_region_codes():
    """The downloaded NVE_Region.shp must expose RØ as UTF-8, not 'RÃ˜'."""
    path = p3.REPO_ROOT / "data/shapefiles/atlas_nve/NVE_Region/NVE_Region.shp"
    if not path.exists():
        print("      (skipped: official NVE_Region.shp not present)")
        return
    frame = p3.read_area_shapefile(path)
    assert set(frame["REGION"]) == {"RS", "RV", "RØ", "RM", "RN"}


def test_east_group_covers_south_and_east():
    """Regression: East is RS + RØ, about 138 366 km2, not RS alone.

    The comparison is made in EPSG:25833 — the source CRS, in metres — because
    the geometry is stored as EPSG:4326 here and an area in square degrees is
    meaningless. 25833 inflates by ~0.2 % against equal-area EPSG:3035, which is
    why the tolerance is 100 km² and not 1.
    """
    path = p3.REPO_ROOT / "data/shapefiles/atlas_nve/NVE_Region/NVE_Region.shp"
    if not path.exists():
        print("      (skipped: official NVE_Region.shp not present)")
        return
    frame = p3.read_area_shapefile(path)
    east = p3.select_area_geometry(frame, "precipitation", "East")
    area = gpd.GeoSeries([east], crs="EPSG:4326").to_crs(25833).area.iloc[0] / 1e6
    assert abs(area - 138_366) < 100, f"East area is {area:,.0f} km2"


def test_weather_cache_name_includes_count():
    first = p3.weather_cache_name(
        "electricity", "NO3", "2024-01-01", "2024-12-31", 24
    )
    second = p3.weather_cache_name(
        "electricity", "NO3", "2024-01-01", "2024-12-31", 1000
    )
    assert first != second


def test_download_region_weather_rejects_bad_interval():
    try:
        p3.download_region_weather("NO3", "2024-12-31", "2024-01-01", count=1)
    except ValueError:
        pass
    else:
        raise AssertionError("reversed dates should raise ValueError")


def test_filling_series_is_regular():
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


def test_stl_decomposition_reconstructs_series():
    series = synthetic_filling()
    fig, result = p3.stl_analysis(series)
    reconstructed = result.trend + result.seasonal + result.resid
    assert np.allclose(reconstructed, series.to_numpy(), atol=1e-8)
    plt.close(fig)


def test_stl_rejects_even_seasonal():
    series = synthetic_filling()
    try:
        p3.stl_analysis(series, seasonal=12)
    except ValueError:
        pass
    else:
        raise AssertionError("even seasonal should raise ValueError")


def test_spectrogram_shapes():
    series = synthetic_filling()
    fig, frequencies, times, power = p3.spectrogram_analysis(series)
    assert power.shape == (frequencies.size, times.size)
    assert np.all(power >= 0)
    plt.close(fig)


def test_satv_removes_constant_signal():
    index = pd.date_range("2024-01-01", periods=366, freq="D")
    series = pd.Series(5.0, index=index, name="constant")
    satv = p3.satv_from_dct(series, cutoff_fraction=0.02)
    assert np.allclose(satv, 0.0, atol=1e-10)


def test_satv_removes_annual_cycle():
    series = synthetic_daily()
    satv = p3.satv_from_dct(series, cutoff_fraction=0.02)
    assert np.std(satv) < 0.5 * np.std(series.to_numpy())


def test_spc_flags_injected_spike():
    index = pd.date_range("2024-01-01", periods=366, freq="D")
    values = np.random.default_rng(0).normal(0, 1, 366)
    values[100] += 15
    series = pd.Series(values, index=index, name="spike")
    fig, outliers = p3.spc_outliers(series, cutoff_fraction=0.02, std_deviations=2.0)
    assert index[100] in outliers.index
    assert set(outliers.columns) == {"value", "satv", "limit_upper", "limit_lower"}
    plt.close(fig)


def test_lof_flags_about_contamination():
    index = pd.date_range("2024-01-01", periods=200, freq="D")
    values = np.random.default_rng(1).normal(0, 1, 200)
    series = pd.Series(values, index=index, name="lof")
    fig, outliers = p3.lof_outliers(series, contamination=0.05)
    assert 8 <= len(outliers) <= 12
    assert set(outliers.columns) == {"value", "lof_score"}
    plt.close(fig)


def test_area_mean_aggregates_locations():
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


def run_tests() -> int:
    """Run every ``test_*`` function and return a shell exit code."""
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as error:  # noqa: BLE001 - the runner reports everything
            failures += 1
            print(f"FAIL {test.__name__}: {error}")
        else:
            print(f"ok   {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
