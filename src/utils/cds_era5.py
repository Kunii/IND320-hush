"""ERA5 downloads from the Copernicus Climate Data Store, exactly as delivered.

This module is the raw layer: it submits one request per year to the CDS
``reanalysis-era5-single-levels`` dataset, caches the GRIB file, and reads the
messages back into numpy arrays. It applies **no** interpolation, no cell
relocation and no elevation correction — what is in the file is what you get.
``src/utils/era5_openmeteo.py`` is the layer that turns these values into the
numbers open-meteo's archive API returns.

Requests are submitted one at a time and never retried more than a few times:
the CDS asks users to stay sequential, and a request with broken syntax retried
500 times (the ``cdsapi`` default) is how accounts get disabled.

Typical use::

    path = fetch_year(2024, ("2m_temperature", "total_precipitation"), [72.5, 4, 56, 40])
    data = read_grib(path)
    frame = to_frame(data, "2t")
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence, cast

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "cache" / "cds"

DATASET = "reanalysis-era5-single-levels"
"""ERA5 hourly data on single levels, 1940 to present, 0.25° grid."""

DEFAULT_AREA = (72.5, 4.0, 56.0, 40.0)
"""North, west, south, east — the box that covers NO1–NO5 and all three
precipitation groups (copied from the CDS download page for this project)."""

MAX_FIELDS_PER_REQUEST = 120_000
"""CDS selection limit for ERA5 hourly single levels. One field is one variable
at one timestep; a year of two hourly variables is 17 520 fields."""

DATA_FORMAT = "grib"
RETRY_MAX = 3
"""Deliberately low: an invalid request must fail fast, not hammer the service."""

MONTHS = tuple(f"{month:02d}" for month in range(1, 13))
DAYS = tuple(f"{day:02d}" for day in range(1, 32))
HOURS = tuple(f"{hour:02d}:00" for hour in range(24))


@dataclass(frozen=True)
class GribData:
    """One downloaded ERA5 file: a regular lat/lon grid and hourly 3-D fields."""

    latitude: np.ndarray
    """Latitudes of the grid, descending, as stored in the file."""

    longitude: np.ndarray
    """Longitudes of the grid, ascending."""

    time: np.ndarray
    """Valid times, ``datetime64[ns]`` in UTC."""

    variables: dict[str, np.ndarray]
    """GRIB ``shortName`` → array of shape ``(time, lat, lon)``, float32."""

    units: dict[str, str] = field(default_factory=dict)

    def shape(self, name: str) -> tuple[int, int, int]:
        return self.variables[name].shape

    def points(self, latitude: Iterable[float], longitude: Iterable[float]) -> pd.DataFrame:
        """Return the series at the nearest grid points as a tidy frame.

        Columns are ``time``, ``lat``, ``lon`` plus one column per variable.
        This is deliberately a nearest-cell lookup with no interpolation: it
        mirrors what the GRIB file contains.
        """
        rows: list[pd.DataFrame] = []
        for lat, lon in zip(latitude, longitude):
            j = int(np.abs(self.latitude - lat).argmin())
            k = int(np.abs(self.longitude - lon).argmin())
            frame = pd.DataFrame({"time": self.time})
            for name, values in self.variables.items():
                frame[name] = values[:, j, k]
            frame["lat"] = float(self.latitude[j])
            frame["lon"] = float(self.longitude[k])
            rows.append(frame)
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def client(quiet: bool = True, url: str | None = None, key: str | None = None):
    """Build a ``cdsapi.Client`` from the repository secrets or given credentials.

    The default key lives in ``.secrets/secrets.toml`` under ``[cdsapi]`` and is
    never read from the environment or printed here. A visitor's own key can be
    passed explicitly (the app's advanced path); it is held in the Streamlit
    session only and never written anywhere.
    """
    import cdsapi

    from src.utils.env import secrets

    return cdsapi.Client(
        url=url or secrets.get_required("cdsapi.url"),
        key=key or secrets.get_required("cdsapi.key"),
        quiet=quiet,
        retry_max=RETRY_MAX,
        sleep_max=60,
    )


def year_request(
    year: int | str,
    variables: Sequence[str],
    area: Sequence[float] = DEFAULT_AREA,
    product_type: str = "reanalysis",
    data_format: str = DATA_FORMAT,
) -> dict[str, Any]:
    """Build a full-year, hourly request for one area box.

    ``variables`` use the CDS names (``2m_temperature``, ``total_precipitation``).
    ``area`` is ``[north, west, south, east]`` in degrees.
    """
    return {
        "product_type": [product_type],
        "variable": list(variables),
        "year": [str(year)],
        "month": list(MONTHS),
        "day": list(DAYS),
        "time": list(HOURS),
        "data_format": data_format,
        "download_format": "unarchived",
        "area": [float(value) for value in area],
    }


def period_request(
    start: str,
    end: str,
    variables: Sequence[str] = ("2m_temperature", "total_precipitation"),
    area: Sequence[float] = DEFAULT_AREA,
    data_format: str = DATA_FORMAT,
) -> dict[str, Any]:
    """Request for an arbitrary inclusive date range (e.g. one month).

    The CDS takes year/month/day lists, so a range that does not start on the
    1st or end on the last day asks for a superset; the caller clips by
    ``valid_time`` after reading. For a calendar month the request is exact.
    """
    days = pd.date_range(start, end, freq="D")
    if days.empty:
        raise ValueError("start must not be after end")
    return {
        "product_type": ["reanalysis"],
        "variable": list(variables),
        "year": sorted({f"{day.year}" for day in days}),
        "month": sorted({f"{day.month:02d}" for day in days}),
        "day": sorted({f"{day.day:02d}" for day in days}),
        "time": list(HOURS),
        "data_format": data_format,
        "download_format": "unarchived",
        "area": [float(value) for value in area],
    }


def field_count(request: dict[str, Any]) -> int:
    """Number of fields (items) a request asks for, for the 120 000 check."""
    years = len(request.get("year", []))
    months = len(request.get("month", []))
    days = len(request.get("day", []))
    hours = len(request.get("time", []))
    variables = len(request.get("variable", []))
    return years * months * days * hours * variables


def request_key(request: dict[str, Any], dataset: str = DATASET) -> str:
    """Stable short hash of a request, used as the cache file name."""
    payload = json.dumps({"dataset": dataset, "request": request}, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def download(
    request: dict[str, Any],
    dataset: str = DATASET,
    refresh: bool = False,
    pause: float = 2.0,
    url: str | None = None,
    key: str | None = None,
) -> Path:
    """Submit one request and return the cached file path.

    The file is named after the request hash, so an identical request is never
    downloaded twice. A short pause follows every submission to keep the client
    sequential and polite. ``url``/``key`` override the repository secrets.
    """
    count = field_count(request)
    if count > MAX_FIELDS_PER_REQUEST:
        raise ValueError(f"request asks for {count} fields; the CDS limit is {MAX_FIELDS_PER_REQUEST}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "grib" if request.get("data_format", DATA_FORMAT) == "grib" else "nc"
    target = CACHE_DIR / f"{request_key(request, dataset)}.{suffix}"
    if target.exists() and not refresh:
        return target

    client(url=url, key=key).retrieve(dataset, request, str(target))
    time.sleep(pause)
    return target


def fetch_year(
    year: int | str,
    variables: Sequence[str] = ("2m_temperature", "total_precipitation"),
    area: Sequence[float] = DEFAULT_AREA,
    refresh: bool = False,
) -> Path:
    """Download one year of hourly ERA5 for one box."""
    return download(year_request(year, variables, area), refresh=refresh)


def fetch_static(
    date: str = "2024-01-01",
    variables: Sequence[str] = ("geopotential", "land_sea_mask"),
    area: Sequence[float] = DEFAULT_AREA,
    refresh: bool = False,
    url: str | None = None,
    key: str | None = None,
) -> Path:
    """Download the time-invariant fields used by the translation layer.

    ``geopotential`` gives the grid-cell orography (``z / 9.80665`` metres) and
    ``land_sea_mask`` marks sea cells, which is how open-meteo stores ``-999``
    in its ERA5 elevation file.
    """
    year, month, day = date.split("-")
    request = {
        "product_type": ["reanalysis"],
        "variable": list(variables),
        "year": [year],
        "month": [month],
        "day": [day],
        "time": ["00:00"],
        "data_format": DATA_FORMAT,
        "download_format": "unarchived",
        "area": [float(value) for value in area],
    }
    return download(request, refresh=refresh, url=url, key=key)


def read_grib(path: str | Path) -> GribData:
    """Read a CDS GRIB file into numpy arrays.

    Uses ``eccodes`` directly rather than cfgrib: the accumulated fields in an
    ERA5 file carry base times six hours before their validity, and cfgrib
    refuses to merge them with instantaneous fields in one dataset. Reading
    ``validityDate``/``validityTime`` per message sidesteps that entirely.
    """
    import eccodes

    path = Path(path)
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    times: dict[Any, None] = {}
    values: dict[tuple[Any, str], np.ndarray] = {}
    units: dict[str, str] = {}

    with path.open("rb") as handle:
        while True:
            message = eccodes.codes_grib_new_from_file(handle)
            if message is None:
                break
            try:
                name = cast(str, eccodes.codes_get(message, "shortName"))
                valid_date = cast(int, eccodes.codes_get(message, "validityDate"))
                valid_time = cast(int, eccodes.codes_get(message, "validityTime"))
                nj = cast(int, eccodes.codes_get(message, "Nj"))
                ni = cast(int, eccodes.codes_get(message, "Ni"))
                stamp = pd.Timestamp(
                    f"{valid_date // 10000:04d}-{valid_date // 100 % 100:02d}-{valid_date % 100:02d} "
                    f"{valid_time // 100:02d}:{valid_time % 100:02d}",
                    tz="UTC",
                )
                field = np.asarray(
                    eccodes.codes_get_values(message), dtype=np.float32
                ).reshape(nj, ni)
                if latitude is None:
                    latitude = np.asarray(
                        eccodes.codes_get_array(message, "latitudes"), dtype=np.float32
                    ).reshape(field.shape)
                    longitude = np.asarray(
                        eccodes.codes_get_array(message, "longitudes"), dtype=np.float32
                    ).reshape(field.shape)
                values[(stamp, name)] = field
                times[stamp] = None
                units.setdefault(name, str(eccodes.codes_get(message, "units")))
            finally:
                eccodes.codes_release(message)

    if latitude is None or not values:
        raise ValueError(f"no GRIB messages found in {path}")

    ordered_times = np.array(
        [stamp.tz_convert("UTC").tz_localize(None).to_datetime64() for stamp in sorted(times)]
    )
    names = sorted({name for _, name in values})
    stacked = {
        name: np.stack([values[(stamp, name)] for stamp in sorted(times)]).astype(np.float32)
        for name in names
        if all((stamp, name) in values for stamp in times)
    }
    return GribData(
        latitude=latitude[:, 0].astype(np.float32),
        longitude=longitude[0, :].astype(np.float32),
        time=ordered_times,
        variables=stacked,
        units={name: units.get(name, "") for name in stacked},
    )


def to_frame(data: GribData, variable: str) -> pd.DataFrame:
    """Flatten one variable to ``time, lat, lon, value`` rows."""
    values = data.variables[variable]
    n_time, n_lat, n_lon = values.shape
    return pd.DataFrame(
        {
            "time": np.repeat(data.time, n_lat * n_lon),
            "lat": np.tile(np.repeat(data.latitude, n_lon), n_time),
            "lon": np.tile(data.longitude, n_time * n_lat),
            "value": values.reshape(-1),
        }
    )
