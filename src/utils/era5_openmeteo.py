"""Turn raw ERA5 into the numbers open-meteo's archive API returns.

open-meteo's ERA5 endpoint is not a plain re-export. Three post-processing
steps sit between the GRIB and the JSON, and this module reproduces all three
from public sources:

1. **Cell selection.** The default ``cell_selection=land`` is not a land mask:
   it is terrain-optimised matching. A 3×3 neighbourhood around the nearest
   cell is searched for the cell whose ERA5 orography is closest to the target
   elevation, with a penalty of 30 m per km of distance
   (``Gridable.findPointTerrainOptimised``). ``cell_selection=nearest`` is the
   plain nearest cell.
2. **Elevation correction.** ``temperature_2m`` is corrected by
   ``(z_era5 - z_target) * 0.0065`` (``GenericReader.scale``). Precipitation is
   untouched.
3. **Rounding.** Both variables are written with one decimal
   (``unit.significantDigits``).

The target elevation is a Copernicus DEM 90 m pixel, read straight from the
AWS Open Data bucket ``s3://copernicus-dem-90m`` with HTTP range requests — the
same product open-meteo used to build its own ``Dem90`` files. The lookup rule
mirrors ``Dem90.read`` exactly, including the integer-metre storage.

Everything here needs the raw fields from :mod:`src.utils.cds_era5`: ``2t``,
``tp`` plus the static ``z`` and ``lsm``.

**How close does it get?** Verified on 2026-01-01, five NO3 points, 120 hours:
cell choice 5/5, elevation 5/5 exact, precipitation exact to float32 epsilon,
temperature 87.5 % identical at one decimal and never more than one 0.1 step
off. The residual is open-meteo's own storage: its temperature arrays are
quantised at about 0.05 K (measured spread ±0.05 K, sd 0.03), so no reader of
the public GRIB can reproduce it bit-for-bit. Values before rounding differ by
0.02 K typically and 0.075 K at worst.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

DEM_URL = "https://copernicus-dem-90m.s3.amazonaws.com/{name}/{name}.tif"
"""Public Copernicus DEM 90 m tiles (AWS Open Data, no credentials)."""

LAPSE_RATE_K_PER_M = 0.0065
"""open-meteo corrects temperature by 0.65 K per 100 m."""

SAME_CELL_TOLERANCE_M = 100.0
"""Terrain matching keeps the nearest cell when it is this close in elevation."""

DISTANCE_PENALTY_M_PER_KM = 30.0
MAX_SEARCH_DISTANCE_KM = 50.0
MAX_MATCH_DELTA = 1500.0
SEARCH_RADIUS = 1
"""ERA5 uses ``RegularGrid(searchRadius: 1)``, i.e. a 3×3 neighbourhood."""

SEA_MARKER = -999.0
"""open-meteo stores sea grid points as -999 in its ERA5 elevation file."""

DECIMALS = {"temperature": 1, "precipitation": 1}

_TILE_CACHE: dict[str, Any] = {}


def _tile_name(latitude: float, longitude: float) -> str:
    """Tile name for the 1°×1° DEM cell that contains the coordinate."""
    north_south = "N" if latitude >= 0 else "S"
    east_west = "E" if longitude >= 0 else "W"
    return (
        f"Copernicus_DSM_COG_30_{north_south}{abs(math.floor(latitude)):02d}_00_"
        f"{east_west}{abs(math.floor(longitude)):03d}_00_DEM"
    )


def dem_width(latitude_floor: int) -> int:
    """Longitude pixels per degree for a latitude band (``Dem90.pixel``).

    The DEM keeps 1 200 rows per degree everywhere and thins out longitude with
    latitude so that pixels stay roughly square.
    """
    for limit, width in (
        (-85, 120),
        (-80, 240),
        (-70, 400),
        (-60, 600),
        (-50, 800),
        (50, 1200),
        (60, 800),
        (70, 600),
        (80, 400),
        (85, 240),
    ):
        if latitude_floor < limit:
            return width
    return 120


def _open_tile(name: str):
    """Open a remote COG, caching the handle (and avoiding directory listings)."""
    if name not in _TILE_CACHE:
        import rasterio

        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_USE_HEAD="NO"):
            _TILE_CACHE[name] = rasterio.open("/vsicurl/" + DEM_URL.format(name=name))
    return _TILE_CACHE[name]


def clear_tile_cache() -> None:
    """Close and forget every open DEM tile."""
    for dataset in _TILE_CACHE.values():
        try:
            dataset.close()
        except Exception:  # pragma: no cover - closing must never raise
            pass
    _TILE_CACHE.clear()


def elevation(latitude: float, longitude: float) -> float:
    """DEM elevation in whole metres, selected exactly as ``Dem90.read`` does.

    Row and column are truncated rather than rounded, the row is counted from
    the south edge, and the value is stored as an integer metre — reproducing
    these three details is what makes the numbers match open-meteo instead of
    landing one pixel off.
    """
    latitude_floor = math.floor(latitude)
    longitude_floor = math.floor(longitude)
    width = dem_width(latitude_floor)
    row_from_south = int((latitude - latitude_floor) * 1200)
    row = 1199 - row_from_south
    column = int((longitude - longitude_floor) * width)

    dataset = _open_tile(_tile_name(latitude, longitude))
    height, tile_width = dataset.height, dataset.width  # type: ignore[attr-defined]
    if height != 1200 or tile_width != width:
        raise ValueError(
            f"unexpected DEM tile shape {tile_width}x{height} for lat {latitude}: expected {width}x1200"
        )
    from rasterio.windows import Window

    window = Window(column, row, 1, 1)
    pixel = float(dataset.read(1, window=window)[0, 0])  # type: ignore[attr-defined]
    return float(round(pixel))


def _round_half_away(value: float) -> int:
    """``roundf`` semantics, used by open-meteo's grid lookup."""
    return int(math.floor(value + 0.5)) if value >= 0 else int(math.ceil(value - 0.5))


def nearest_cell(
    latitude: float,
    longitude: float,
    grid_latitude: np.ndarray | Sequence[float],
    grid_longitude: np.ndarray | Sequence[float],
) -> tuple[int, int]:
    """Index of the nearest ERA5 cell; ``grid_latitude`` may ascend or descend."""
    lat = np.asarray(grid_latitude, dtype=float)
    lon = np.asarray(grid_longitude, dtype=float)
    step_lat = abs(lat[1] - lat[0])
    step_lon = abs(lon[1] - lon[0])
    # open-meteo rounds on a global grid; doing it on the local grid gives the
    # same cell as long as the subset is aligned to the 0.25° lattice.
    row = _round_half_away((latitude - float(lat[0])) / (lat[1] - lat[0]))
    column = _round_half_away((longitude - float(lon[0])) / step_lon)
    row = min(max(row, 0), lat.size - 1)
    column = min(max(column, 0), lon.size - 1)
    if abs(float(lon[column]) - longitude) > step_lon:  # misaligned subset guard
        column = int(np.abs(lon - longitude).argmin())
    if abs(float(lat[row]) - latitude) > step_lat:
        row = int(np.abs(lat - latitude).argmin())
    return row, column


def select_cell(
    latitude: float,
    longitude: float,
    target_elevation: float,
    grid_latitude: np.ndarray | Sequence[float],
    grid_longitude: np.ndarray | Sequence[float],
    model_elevation: np.ndarray,
    mode: str = "land",
) -> tuple[int, int]:
    """Which ERA5 cell open-meteo would read for this coordinate.

    ``mode`` is open-meteo's ``cell_selection``: ``"nearest"`` returns the
    nearest cell, ``"land"`` runs the terrain-optimised search against
    ``model_elevation`` (the ERA5 orography grid, sea cells marked -999).
    """
    row, column = nearest_cell(latitude, longitude, grid_latitude, grid_longitude)
    if mode == "nearest":
        return row, column
    if mode != "land":
        raise ValueError(f"unsupported cell selection mode {mode!r}")
    if not np.isfinite(target_elevation):
        return row, column

    centre = float(model_elevation[row, column])
    delta_centre = abs(centre - target_elevation)
    if delta_centre <= SAME_CELL_TOLERANCE_M:
        return row, column

    lat = np.asarray(grid_latitude, dtype=float)
    lon = np.asarray(grid_longitude, dtype=float)
    best_delta = delta_centre
    best: tuple[int, int] | None = None
    best_elevation = float("nan")

    for y in range(max(row - SEARCH_RADIUS, 0), min(row + SEARCH_RADIUS + 1, lat.size)):
        for x in range(max(column - SEARCH_RADIUS, 0), min(column + SEARCH_RADIUS + 1, lon.size)):
            value = float(model_elevation[y, x])
            if not np.isfinite(value) or value <= SEA_MARKER:
                continue
            distance_km = math.hypot(float(lat[y]) - latitude, float(lon[x]) - longitude) * 111.0
            delta = abs(value - target_elevation) + distance_km * DISTANCE_PENALTY_M_PER_KM
            if delta < best_delta and distance_km < MAX_SEARCH_DISTANCE_KM:
                best_delta = delta
                best = (y, x)
                best_elevation = value

    if best is None or best_delta > MAX_MATCH_DELTA:
        return row, column
    if not np.isfinite(best_elevation):  # pragma: no cover - defensive
        return row, column
    return best


def temperature_celsius(
    temperature_kelvin: np.ndarray,
    model_elevation: float,
    target_elevation: float,
) -> np.ndarray:
    """Kelvin → °C with open-meteo's lapse-rate correction to the target elevation."""
    celsius = np.asarray(temperature_kelvin, dtype=np.float64) - 273.15
    if np.isfinite(model_elevation) and np.isfinite(target_elevation):
        if float(model_elevation) != float(target_elevation):
            celsius = celsius + (float(model_elevation) - float(target_elevation)) * LAPSE_RATE_K_PER_M
    return celsius


def precipitation_mm(total_precipitation_m: np.ndarray) -> np.ndarray:
    """ERA5 ``tp`` is metres of accumulated water; open-meteo reports mm."""
    return np.asarray(total_precipitation_m, dtype=np.float32) * np.float32(1000.0)


def model_elevation_grid(
    geopotential: np.ndarray,
    land_sea_mask: np.ndarray,
) -> np.ndarray:
    """Build open-meteo's ERA5 elevation grid: ``z / 9.80665``, sea at -999.

    The grid is ``(lat, lon)``; pass a single timestep of the static fields.
    """
    elevation_m = np.asarray(geopotential, dtype=np.float32) / np.float32(9.80665)
    sea = np.asarray(land_sea_mask, dtype=np.float32) < 0.5
    return np.where(sea, np.float32(SEA_MARKER), elevation_m).astype(np.float32)


def series_for_point(
    latitude: float,
    longitude: float,
    grid_latitude: Sequence[float],
    grid_longitude: Sequence[float],
    temperature_kelvin: np.ndarray,
    precipitation: np.ndarray,
    model_elevation: np.ndarray,
    mode: str = "land",
    round_output: bool = True,
) -> dict[str, object]:
    """One point as open-meteo would return it.

    ``temperature_kelvin`` and ``precipitation`` are ``(time, lat, lon)`` arrays
    from :class:`cds_era5.GribData`; ``model_elevation`` is ``(lat, lon)``.
    """
    target = elevation(latitude, longitude)
    row, column = select_cell(
        latitude, longitude, target, grid_latitude, grid_longitude, model_elevation, mode=mode
    )
    cell_elevation = float(model_elevation[row, column])
    if cell_elevation <= SEA_MARKER:
        cell_elevation = 0.0

    temperature = temperature_celsius(temperature_kelvin[:, row, column], cell_elevation, target)
    rain = precipitation_mm(precipitation[:, row, column])
    if round_output:
        temperature = np.round(temperature, DECIMALS["temperature"])
        rain = np.round(rain, DECIMALS["precipitation"])

    return {
        "latitude": float(grid_latitude[row]),
        "longitude": float(grid_longitude[column]),
        "elevation": target,
        "model_elevation": cell_elevation,
        "temperature_2m": temperature,
        "precipitation": rain,
    }


def frame_for_points(
    points: pd.DataFrame,
    grid_latitude: Sequence[float],
    grid_longitude: Sequence[float],
    temperature_kelvin: np.ndarray,
    precipitation: np.ndarray,
    model_elevation: np.ndarray,
    time: Iterable,
    mode: str = "land",
) -> pd.DataFrame:
    """Translate many points and return a tidy frame.

    ``points`` needs ``lat`` and ``lon`` columns in EPSG:4326. The frame has one
    row per point and timestamp with open-meteo's column names and precision.
    """
    times = np.asarray(list(time))
    frames: list[pd.DataFrame] = []
    for index, point in points.iterrows():
        latitude = float(np.asarray(point["lat"], dtype=float))
        longitude = float(np.asarray(point["lon"], dtype=float))
        result = series_for_point(
            latitude,
            longitude,
            grid_latitude,
            grid_longitude,
            temperature_kelvin,
            precipitation,
            model_elevation,
            mode=mode,
        )
        frames.append(
            pd.DataFrame(
                {
                    "point": index,
                    "time": times,
                    "temperature_2m": result["temperature_2m"],
                    "precipitation": result["precipitation"],
                    "cell_lat": result["latitude"],
                    "cell_lon": result["longitude"],
                    "elevation": result["elevation"],
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
