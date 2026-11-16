"""Write ERA5 area-mean caches in the schema the notebook and app already read.

The existing caches (``data/cache/weather_*``) hold four columns — the time
axis, ``temperature_2m``, ``precipitation`` and ``point_count`` — and nothing
else, so this module writes exactly that. Two ways of building the area mean
are supported:

``mode="points"``
    The semantics of ``download_region_weather`` in the notebook: average the
    series of the sampled locations. Point values are translated to open-meteo
    equivalents by :mod:`src.utils.era5_openmeteo`, so a cache built this way
    matches the open-meteo one to within a display decimal.

``mode="grid"``
    Every 0.25° cell whose centre falls inside the polygon, weighted by
    ``cos(lat)``. This removes the sampling noise of the 1 000-point draw (about
    0.1 K on a winter day) and cannot be done through the API at all.

Files carry a ``_cds`` suffix, so they never overwrite a cache that was
downloaded through open-meteo; ``overwrite=True`` is required to replace one.

Example::

    from src.utils.era5_cache import build_area_cache

    path = build_area_cache("electricity", "NO3", "2024-01-01", "2024-12-31",
                            mode="grid", resolution="hourly")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from src.utils.cds_era5 import (
    DEFAULT_AREA,
    GribData,
    download,
    fetch_static,
    fetch_year,
    period_request,
    read_grib,
)
from src.utils.era5_openmeteo import (
    LAPSE_RATE_K_PER_M,
    SEA_MARKER,
    elevation,
    model_elevation_grid,
    select_cell,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache"

HOURLY_COLUMNS = ("timestamp", "temperature_2m", "precipitation", "point_count")
DAILY_COLUMNS = ("date", "temperature_2m", "precipitation", "point_count")


def cache_name(
    kind: str,
    name: str,
    start_date: str,
    end_date: str,
    label: str,
    resolution: str = "hourly",
) -> str:
    """File stem for a CDS-built cache.

    ``label`` is the number of sampled points (``1000``) or ``grid<cells>``;
    the ``_cds`` suffix marks the source so an open-meteo cache is never
    overwritten by accident.
    """
    return f"weather_{kind}_{name}_{start_date}_{end_date}_{label}_{resolution}_cds"


def _area_for(points: pd.DataFrame | None, geometry: Any | None) -> list[float]:
    """Smallest CDS area box that covers the points or the polygon."""
    if geometry is not None:
        west, south, east, north = (float(value) for value in geometry.bounds)
    elif points is not None:
        latitude = points["lat"].to_numpy(dtype=float)
        longitude = points["lon"].to_numpy(dtype=float)
        south, north = float(latitude.min()), float(latitude.max())
        west, east = float(longitude.min()), float(longitude.max())
    else:
        return list(DEFAULT_AREA)
    south = max(np.floor(south * 4) / 4 - 0.25, -90.0)
    west = max(np.floor(west * 4) / 4 - 0.25, -180.0)
    north = min(np.ceil(north * 4) / 4 + 0.25, 90.0)
    east = min(np.ceil(east * 4) / 4 + 0.25, 180.0)
    return [north, west, south, east]


def _hull(points: pd.DataFrame):
    """Convex hull of a points frame, used when no polygon is supplied."""
    import geopandas as gpd

    return gpd.GeoSeries(
        gpd.points_from_xy(points["lon"], points["lat"]), crs="EPSG:4326"
    ).union_all()


def _grid_mask(geometry: Any, latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    """Cells whose centre falls inside the polygon."""
    import shapely

    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    return np.asarray(shapely.contains_xy(geometry, lon_grid, lat_grid))


def _translate_points(
    points: pd.DataFrame,
    data: GribData,
    model_elevation: np.ndarray,
    mode: str,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Translate sampled points into ``(time, point)`` matrices.

    Returns temperature in °C and precipitation in mm plus one metadata row per
    point (cell coordinates, DEM elevation, model elevation). One DEM lookup per
    point, then a single vectorised correction.
    """
    targets: list[float] = []
    rows: list[int] = []
    columns: list[int] = []
    for latitude, longitude in points[["lat", "lon"]].to_numpy(dtype=float):
        target = elevation(latitude, longitude)
        row, column = select_cell(
            latitude, longitude, target, data.latitude, data.longitude, model_elevation, mode=mode
        )
        targets.append(target)
        rows.append(row)
        columns.append(column)

    row_index = np.asarray(rows)
    column_index = np.asarray(columns)
    target_elevation = np.asarray(targets, dtype=np.float64)
    cell_elevation = model_elevation[row_index, column_index].astype(np.float64)
    cell_elevation = np.where(cell_elevation <= SEA_MARKER, 0.0, cell_elevation)

    temperature = data.variables["2t"][:, row_index, column_index].astype(np.float64) - 273.15
    temperature = temperature + (cell_elevation - target_elevation)[None, :] * LAPSE_RATE_K_PER_M
    precipitation = data.variables["tp"][:, row_index, column_index].astype(np.float64) * 1000.0

    meta = pd.DataFrame(
        {
            "lat": points["lat"].astype(float).to_numpy(),
            "lon": points["lon"].astype(float).to_numpy(),
            "cell_lat": data.latitude[row_index].astype(float),
            "cell_lon": data.longitude[column_index].astype(float),
            "elevation": target_elevation,
            "model_elevation": cell_elevation,
        }
    )
    return temperature, precipitation, meta


def _translate_grid(
    data: GribData, geometry: Any, model_elevation: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Translate every grid cell inside the polygon into ``(time, cell)`` matrices.

    No elevation correction is applied: a polygon mean is already at the cell
    scale, so there is no "requested point" to correct towards.
    """
    mask = _grid_mask(geometry, data.latitude, data.longitude)
    if not mask.any():
        raise ValueError("no ERA5 grid cell falls inside the polygon")
    temperature = data.variables["2t"][:, mask].astype(np.float64) - 273.15
    precipitation = data.variables["tp"][:, mask].astype(np.float64) * 1000.0
    latitude_grid = np.broadcast_to(data.latitude[:, None], mask.shape)
    weights = np.cos(np.deg2rad(latitude_grid[mask].astype(np.float64)))
    return temperature, precipitation, weights, int(mask.sum())


def _collapse(values: np.ndarray, weights: np.ndarray | None) -> np.ndarray:
    """Mean over locations, weighted when a weight vector is given."""
    if weights is None:
        return values.mean(axis=1)
    return np.average(values, axis=1, weights=weights)


def parity_round(
    temperature: np.ndarray, precipitation: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Round per-point values to the one decimal open-meteo publishes.

    Averaging rounded values is not the same as averaging raw ones: for a
    thousand points the annual precipitation total moves by ~1.1 %, because
    every point is first snapped to the 0.1 mm grid the API returns.
    """
    return np.round(temperature, 1), np.round(precipitation, 1)


def _daily(frame: pd.DataFrame) -> pd.DataFrame:
    """Hourly area means to daily means (temperature) and sums (precipitation)."""
    indexed = frame.set_index("timestamp")
    daily = indexed.resample("1D").agg(
        {"temperature_2m": "mean", "precipitation": "sum", "point_count": "mean"}
    )
    daily["point_count"] = daily["point_count"].round().astype("int64")
    daily.index.name = "date"
    return daily.reset_index()


def build_range_frame(
    points: pd.DataFrame,
    start: str,
    end: str,
    *,
    url: str | None = None,
    key: str | None = None,
    area: Sequence[float] = DEFAULT_AREA,
    resolution: str = "hourly",
    parity: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """One date range from the CDS, in the shipped cache schema, in memory.

    This is the app's "bring your own CDS key" path: it submits **one** request
    for the box and returns the translated frame without writing a cache. Use
    ``build_area_cache`` when a file is wanted.

    A month is ~1 500 fields (a few MB); the CDS queue usually takes minutes,
    which is why this is an advanced control and not the default source.
    """
    if resolution not in {"hourly", "daily"}:
        raise ValueError("resolution must be 'hourly' or 'daily'")
    request = period_request(start, end, area=area)
    data = read_grib(download(request, refresh=refresh, url=url, key=key))
    static = read_grib(fetch_static(area=area, url=url, key=key))
    model_elevation = model_elevation_grid(
        static.variables["z"][0], static.variables["lsm"][0]
    )
    if model_elevation.shape != (data.latitude.size, data.longitude.size):
        raise ValueError(
            "the static fields and the downloaded grid have different shapes; "
            "both requests must use the same `area`"
        )

    temperature, precipitation, _meta = _translate_points(
        points, data, model_elevation, "land"
    )
    if parity:
        temperature, precipitation = parity_round(temperature, precipitation)

    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(data.time, utc=True),
            "temperature_2m": _collapse(temperature, None),
            "precipitation": _collapse(precipitation, None),
            "point_count": np.full(temperature.shape[0], len(points), dtype="int64"),
        }
    )
    in_range = (frame["timestamp"] >= pd.Timestamp(start, tz="UTC")) & (
        frame["timestamp"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    )
    frame = frame.loc[in_range].reset_index(drop=True)
    if frame.empty:
        raise ValueError("no rows left after clipping to the requested dates")
    return _daily(frame) if resolution == "daily" else frame


def write_area_cache(
    frame: pd.DataFrame,
    path: Path,
    resolution: str = "hourly",
    overwrite: bool = False,
) -> Path:
    """Write one cache file after checking the schema."""
    expected = HOURLY_COLUMNS if resolution == "hourly" else DAILY_COLUMNS
    if tuple(frame.columns) != expected:
        raise ValueError(f"columns {tuple(frame.columns)} do not match {expected}")
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists; pass overwrite=True to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def build_area_cache(
    kind: str,
    name: str,
    start_date: str,
    end_date: str,
    *,
    mode: str = "grid",
    points: pd.DataFrame | None = None,
    geometry: Any | None = None,
    resolution: str = "hourly",
    area: Sequence[float] | None = None,
    cell_selection: str = "land",
    parity: bool = False,
    output_dir: str | Path | None = None,
    grib_paths: Sequence[str | Path] | None = None,
    overwrite: bool = False,
    verbose: bool = True,
) -> Path:
    """Build and write one area-mean cache from CDS ERA5.

    Parameters
    ----------
    kind, name:
        Layer and region, used for the file name — ``electricity``/``NO3`` or
        ``precipitation``/``East``.
    start_date, end_date:
        Inclusive ISO dates. A range spanning several years submits one request
        per year, sequentially.
    mode:
        ``"grid"`` (default) averages every 0.25° cell inside ``geometry``,
        weighted by ``cos(lat)``. ``"points"`` reproduces the notebook's
        sampled-location semantics and needs ``points``.
    points:
        DataFrame with ``lat``/``lon`` columns (EPSG:4326). Used directly in
        points mode and as the convex hull when grid mode has no geometry.
    geometry:
        Shapely polygon for grid mode.
    resolution:
        ``"hourly"`` or ``"daily"``; daily aggregates temperature by mean and
        precipitation by sum, exactly like ``download_region_weather``.
    area:
        CDS ``[north, west, south, east]`` box; derived from the data by default.
    cell_selection:
        open-meteo's ``cell_selection`` for point translation (``"land"`` or
        ``"nearest"``).
    parity:
        Points mode only. Round every point to open-meteo's one-decimal output
        *before* averaging, which reproduces the API series instead of the
        raw ERA5 field. Measured 2024, NO3, 1000 points: temperature bias
        −0.007 K (max 0.015 K), precipitation identical. Without it the annual
        precipitation total is 1.1 % high, because averaging unrounded values
        is not the same as averaging the API's rounded ones.
    output_dir:
        Where the parquet goes; ``data/cache`` by default. The app's caches
        live in ``data/precomputed/weather``.
    grib_paths:
        Pre-downloaded files; when given, nothing is submitted to the CDS.
    """
    if mode not in {"grid", "points"}:
        raise ValueError("mode must be 'grid' or 'points'")
    if resolution not in {"hourly", "daily"}:
        raise ValueError("resolution must be 'hourly' or 'daily'")
    if mode == "points" and points is None:
        raise ValueError("points mode needs a points frame")
    if parity and mode != "points":
        raise ValueError(
            "parity is only defined for points mode: grid mode has no point "
            "series to round before averaging"
        )
    if geometry is None and points is not None:
        geometry = _hull(points)
    if mode == "grid" and geometry is None:
        raise ValueError("grid mode needs a geometry")

    start = pd.Timestamp(start_date).date().isoformat()
    end = pd.Timestamp(end_date).date().isoformat()
    if pd.Timestamp(start) > pd.Timestamp(end):
        raise ValueError("start_date must not be after end_date")

    box = list(area) if area is not None else _area_for(points, geometry)

    static = read_grib(fetch_static(area=box))
    model_elevation = model_elevation_grid(
        static.variables["z"][0], static.variables["lsm"][0]
    )

    if grib_paths is None:
        grib_paths = [
            fetch_year(year, area=box)
            for year in range(pd.Timestamp(start).year, pd.Timestamp(end).year + 1)
        ]

    chunks: list[pd.DataFrame] = []
    cells = 0
    for path in (Path(item) for item in grib_paths):
        data = read_grib(path)
        if model_elevation.shape != (data.latitude.size, data.longitude.size):
            raise ValueError(
                f"static fields are {model_elevation.shape} but {path.name} is "
                f"{(data.latitude.size, data.longitude.size)}; the same `area` "
                "must be used for the year and the static download"
            )
        if mode == "points":
            assert points is not None
            temperature, precipitation, meta = _translate_points(
                points, data, model_elevation, cell_selection
            )
            if parity:
                # open-meteo writes one decimal per point; averaging the
                # rounded values is not the same as averaging the raw field.
                temperature, precipitation = parity_round(temperature, precipitation)
            weights = None
            count = len(meta)
        else:
            temperature, precipitation, weights, count = _translate_grid(
                data, geometry, model_elevation
            )
            cells = count

        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(data.time, utc=True),
                "temperature_2m": _collapse(temperature, weights),
                "precipitation": _collapse(precipitation, weights),
                "point_count": np.full(temperature.shape[0], int(count), dtype="int64"),
            }
        )
        chunks.append(frame)
        if verbose:
            print(f"  {path.name}: {len(frame):,} rows from {count} locations")

    frame = pd.concat(chunks, ignore_index=True)
    frame = frame[
        (frame["timestamp"] >= pd.Timestamp(start, tz="UTC"))
        & (frame["timestamp"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1))
    ]
    frame = frame.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    if frame.empty:
        raise ValueError("no rows left after clipping to the requested dates")

    if resolution == "daily":
        frame = _daily(frame)

    label = f"grid{cells}" if mode == "grid" else str(len(points) if points is not None else 0)
    directory = Path(output_dir) if output_dir is not None else CACHE_DIR
    path = directory / f"{cache_name(kind, name, start, end, label, resolution)}.parquet"
    return write_area_cache(frame, path, resolution=resolution, overwrite=overwrite)
