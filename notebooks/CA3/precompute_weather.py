"""Precompute ERA5 area-mean weather caches for the CA3 app.

Why this exists
---------------
open-meteo's free tier allows 10,000 weighted calls per day and 5,000 per hour.
A request's weight is

    weight = n_locations * (n_days / 14) * (n_variables / 10)

so 1000 locations x 2 variables x one year is about 5,200 weighted calls for a
single area. The app can select eight areas, which would need roughly 42,000
calls (about five days at the free-tier rate) if it downloaded on demand.

Design (2026-11-10 revision)
----------------------------
* **Projected sampling.** The 1000-point pool is drawn in EPSG:3035
  (equal-area), not in degrees. Sampling in EPSG:4326 is uniform per square
  degree, which at Norwegian latitudes puts about 3x more points per km² in the
  north of an area than in the south; EPSG:3035 makes a random point equally
  likely per km². This is the one place in the project that samples, so it is
  also the place where the choice matters. See ``docs/crs.md``.
* **Land clipping.** The raw NVE areas include the sea out to the territorial
  border (NO3 is 63 % land, NO4 57 %, North 59 %). Each area is intersected with
  NVE's ``Norge_N5000`` land layer before sampling.
* **Grid de-duplication.** Points are snapped to the ERA5 0.25 degree grid;
  duplicate cells and cell centres that fall back in the sea are removed.
  ``--cells`` chooses how many unique cells per area to request (small areas
  cap at what is available).
* **Hourly output.** The API returns hourly values; this script stores hourly
  area means (8,784 rows per area-year) instead of daily aggregates. That costs
  no extra quota and keeps the SPC/LOF resolution at the level the task and the
  textbook 3-sigma default expect.
* **Checkpointing.** Each batch of 8 locations is written to
  ``data/cache/parts/<cache name>/`` so a 429 wait or a crash does not lose
  completed work.

Usage
-----
    # Show the plan and the weighted-call cost. No ERA5 calls and no weather
    # files are written; the NVE land mask may be cached.
    .venv/bin/python notebooks/CA3/precompute_weather.py --dry-run

    # Download all eight areas for 2024, 100 grid cells per area.
    .venv/bin/python notebooks/CA3/precompute_weather.py --year 2024 --cells 100

    # One area, custom interval, daily output.
    .venv/bin/python notebooks/CA3/precompute_weather.py \
        --regions NO3 --start 2024-01-01 --end 2024-12-31 \
        --cells 100 --resolution daily

The default budget is 4,800 weighted calls, just under the hourly limit, so a
single invocation is unlikely to trigger a 429. Existing caches are skipped, so
a later invocation resumes where the previous one stopped.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path(__file__).with_name("Proj-P3.py")
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "precomputed" / "weather"
MANIFEST_NAME = "weather_manifest.json"

NVE_LAND_URL = (
    "https://kart.nve.no/enterprise/rest/services/"
    "Mapservices/Administrasjon2/MapServer/11/query"
)
LAND_FIELD = "OBJTYPE"
SEA_VALUE = "Havflate"


def load_analysis_module():
    """Import Proj-P3.py despite the hyphen in its filename."""
    spec = importlib.util.spec_from_file_location("proj_p3", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["proj_p3"] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    first_line = (__doc__ or "Precompute ERA5 caches").splitlines()[0]
    parser = argparse.ArgumentParser(description=first_line)
    parser.add_argument(
        "--regions",
        default="all",
        help="Comma-separated area names, or 'all' (default: all eight areas).",
    )
    parser.add_argument("--year", type=int, default=2024, help="Calendar year.")
    parser.add_argument("--start", help="Start date (overrides --year).")
    parser.add_argument("--end", help="End date (overrides --year).")
    parser.add_argument(
        "--cells",
        type=int,
        default=100,
        help="Unique 0.25 degree ERA5 cells to request per area (default: 100).",
    )
    parser.add_argument(
        "--pool",
        type=int,
        default=1000,
        help="Locations sampled per area before collapsing to grid cells.",
    )
    parser.add_argument(
        "--resolution",
        choices=("hourly", "daily"),
        default="hourly",
        help="Store hourly area means (default) or daily aggregates.",
    )
    parser.add_argument(
        "--no-land",
        action="store_true",
        help="Do not clip the areas to land (reproduces the old behaviour).",
    )
    parser.add_argument(
        "--sample-crs",
        type=int,
        default=3035,
        help="Projected CRS used for sampling (default: 3035, equal-area).",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=4800.0,
        help="Maximum weighted calls for this invocation (default: 4800).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and cost without ERA5 calls or weather files.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download even when a weather cache already exists.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for the committable parquet copies.",
    )
    return parser.parse_args()


def selected_regions(module, value: str) -> list[tuple[str, str]]:
    """Return (kind, name) pairs for the requested region names."""
    electricity = list(module.ELECTRICITY_AREAS)
    precipitation = list(module.PRECIPITATION_GROUPS)
    if value.strip().lower() == "all":
        return [("electricity", name) for name in electricity] + [
            ("precipitation", name) for name in precipitation
        ]

    pairs: list[tuple[str, str]] = []
    for name in (part.strip() for part in value.split(",") if part.strip()):
        pairs.append((module.region_kind(name), name))
    return pairs


def interval(args: argparse.Namespace, module) -> tuple[str, str]:
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start and --end must be given together")
        start, end = args.start, args.end
    else:
        start, end = f"{args.year}-01-01", f"{args.year}-12-31"

    start_date = pd.Timestamp(start).date().isoformat()
    end_date = pd.Timestamp(end).date().isoformat()
    if pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise SystemExit("start date must not be after end date")
    return start_date, end_date


def land_union(module, sample_crs: int, refresh: bool = False):
    """Load NVE's land polygons (everything except sea) in the sampling CRS.

    The ArcGIS layer is requested with ``outSR=4326`` (what GeoJSON means) and
    reprojected to ``sample_crs`` — EPSG:3035 by default — so the clip and the
    sampling happen in the same equal-area space.
    """
    cache = module.CACHE_DIR / "norway_land.geojson"
    if not cache.exists() or refresh:
        response = requests.get(
            NVE_LAND_URL,
            params={
                "where": f"{LAND_FIELD} <> '{SEA_VALUE}'",
                "outFields": LAND_FIELD,
                "outSR": 4326,
                "f": "geojson",
            },
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"NVE land layer error: {payload['error']}")
        if payload.get("exceededTransferLimit"):
            raise RuntimeError("NVE land layer was truncated (transfer limit)")
        cache.write_text(response.text, encoding="utf-8")
        print(f"Downloaded land mask -> {cache.name}")

    land = gpd.read_file(cache)
    return land.to_crs(sample_crs).geometry.union_all()


def projected_geometry(
    module, kind: str, name: str, args: argparse.Namespace, land
):
    """Return the area geometry in the sampling CRS, optionally clipped to land.

    Input geometry is EPSG:4326 (from ``download_area_layer``); the returned
    geometry is ``args.sample_crs`` (EPSG:3035 by default, equal-area), which is
    also the space the reported ``raw_km2``/``land_km2`` are measured in.
    """
    areas = module.download_area_layer(kind)
    geometry = module.select_area_geometry(areas, kind, name)
    projected = gpd.GeoSeries([geometry], crs="EPSG:4326").to_crs(args.sample_crs)
    raw_km2 = float(projected.area.iloc[0]) / 1e6

    if args.no_land:
        clipped = projected.iloc[0]
    else:
        clipped = projected.intersection(land).buffer(0).iloc[0]

    if clipped.is_empty:
        raise RuntimeError(f"{name}: area is empty after land clipping")
    land_km2 = float(gpd.GeoSeries([clipped], crs=args.sample_crs).area.iloc[0]) / 1e6
    return clipped, raw_km2, land_km2


def sample_pool(
    geometry, count: int, sample_crs: int, seed: int
) -> pd.DataFrame:
    """Draw ``count`` uniform points in the projected CRS and return WGS84 lon/lat.

    Uniform is per km² here because ``geometry`` and the draw are in
    ``sample_crs`` (EPSG:3035, equal-area). The result is converted to
    EPSG:4326 for open-meteo and for the 0.25 degree grid snap that follows.
    """
    multipoint = (
        gpd.GeoSeries([geometry], crs=sample_crs)
        .sample_points(count, rng=seed)
        .iloc[0]
    )
    x = [point.x for point in multipoint.geoms]
    y = [point.y for point in multipoint.geoms]
    wgs84 = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=sample_crs).to_crs(4326)
    return pd.DataFrame({"lon": wgs84.x.to_numpy(), "lat": wgs84.y.to_numpy()})


def grid_cells(points: pd.DataFrame) -> pd.DataFrame:
    """Snap WGS84 points to 0.25 degree ERA5 cells and keep unique cells.

    Stays in EPSG:4326 on purpose: ERA5 is published on a regular 0.25 degree
    grid, so snapping is only meaningful in degrees, and two pool points that
    land in one cell must collapse to a single request.
    """
    snapped = pd.DataFrame(
        {
            "lon": (points["lon"].to_numpy() * 4).round() / 4,
            "lat": (points["lat"].to_numpy() * 4).round() / 4,
        }
    )
    return snapped.drop_duplicates().reset_index(drop=True)


def cells_on_land(cells: pd.DataFrame, land, sample_crs: int) -> pd.DataFrame:
    """Drop cell centres that fall back in the sea after snapping.

    ``cells`` are EPSG:4326 lon/lat (the ERA5 grid); they are reprojected to
    ``sample_crs`` to test against the land union, which lives in that space.
    """
    centres = gpd.GeoSeries(
        gpd.points_from_xy(cells["lon"], cells["lat"]), crs="EPSG:4326"
    ).to_crs(sample_crs)
    return cells.loc[centres.within(land).to_numpy()].reset_index(drop=True)


def choose_cells(cells: pd.DataFrame, count: int, seed: int) -> pd.DataFrame:
    """Choose up to ``count`` cells, deterministically."""
    if len(cells) <= count:
        return cells.reset_index(drop=True)
    chosen = cells.sample(n=count, random_state=seed)
    return chosen.sort_values(["lat", "lon"]).reset_index(drop=True)


def weighted_calls(n_locations: int, start: str, end: str, module) -> float:
    """open-meteo weight for one request set, per their published formula."""
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    variables = len(module.ERA5_VARIABLES)
    return n_locations * (days / 14) * (variables / 10)


def cache_names(
    kind: str,
    name: str,
    start: str,
    end: str,
    cells: int,
    land: bool,
    sample_crs: int,
    resolution: str,
) -> tuple[str, str]:
    """Cache names encode every choice that changes the values."""
    surface = "land" if land else "sea"
    weather = (
        f"weather_{kind}_{name}_{start}_{end}"
        f"_c{cells}_{surface}{sample_crs}_{resolution}"
    )
    points = f"points_{kind}_{name}_c{cells}_{surface}{sample_crs}"
    return weather, points


def fetch_hourly(
    points: pd.DataFrame,
    start: str,
    end: str,
    parts_dir: Path,
    module,
    batch_size: int | None = None,
    pause: float | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Download hourly ERA5 data with one checkpoint file per batch."""
    variables = module.ERA5_VARIABLES
    batch_size = batch_size or module.API_BATCH_SIZE
    pause = module.API_PAUSE_SECONDS if pause is None else pause
    parts_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    total = len(points)
    for begin in range(0, total, batch_size):
        batch = points.iloc[begin : begin + batch_size]
        part = parts_dir / f"batch_{begin:05d}.parquet"

        if part.exists() and not refresh:
            frames.append(pd.read_parquet(part))
            print(f"  {min(begin + batch_size, total)}/{total} (cached part)")
            continue

        params = {
            "latitude": ",".join(f"{value:.6f}" for value in batch["lat"]),
            "longitude": ",".join(f"{value:.6f}" for value in batch["lon"]),
            "start_date": start,
            "end_date": end,
            "hourly": ",".join(variables),
            "models": "era5",
            "timezone": "UTC",
        }
        response = module._request_with_retry(module.ERA5_URL, params)
        payload = response.json()
        if isinstance(payload, dict):  # single-location responses are not lists
            payload = [payload]

        batch_frames = []
        for item in payload:
            frame = pd.DataFrame(item["hourly"])
            frame["timestamp"] = pd.to_datetime(frame.pop("time"), utc=True)
            frame["lat"] = float(item["latitude"])
            frame["lon"] = float(item["longitude"])
            batch_frames.append(frame)

        part_frame = pd.concat(batch_frames, ignore_index=True)
        part_frame.to_parquet(part, index=False)
        frames.append(part_frame)
        print(f"  {min(begin + batch_size, total)}/{total} downloaded")
        time.sleep(pause)

    return pd.concat(frames, ignore_index=True)


def area_mean(
    weather: pd.DataFrame, resolution: str, module
) -> pd.DataFrame:
    """Average the per-location series over each hour (or day)."""
    hourly = module.area_mean(weather)  # groups by timestamp, adds point_count
    hourly.index.name = "timestamp"

    if resolution == "hourly":
        return hourly

    daily = hourly.resample("1D").agg(
        {"temperature_2m": "mean", "precipitation": "sum", "point_count": "mean"}
    )
    daily.index.name = "date"
    return daily


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"generated_at": None, "entries": []}


def save_manifest(path: Path, manifest: dict) -> None:
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    module = load_analysis_module()
    start, end = interval(args, module)
    regions = selected_regions(module, args.regions)
    land = None if args.no_land else land_union(module, args.sample_crs)

    manifest_path = args.out_dir / MANIFEST_NAME
    manifest = load_manifest(manifest_path)

    print(f"Interval: {start} -> {end}")
    print(f"Sampling: {args.pool} points per area in EPSG:{args.sample_crs}")
    print(f"Land clipping: {'off' if args.no_land else 'on'}")
    print(f"Requested cells per area: {args.cells}")
    print(f"Resolution: {args.resolution}")
    print(f"Budget: {args.budget:,.0f} weighted calls")
    print()

    header = (
        f"{'area':<10}{'raw km2':>9}{'land km2':>10}"
        f"{'avail':>7}{'cells':>7}{'weight':>9}  status"
    )
    print(header)
    print("-" * len(header))

    spent = 0.0
    planned = 0.0
    total_cells = 0
    total_available = 0

    for kind, name in regions:
        weather_name, points_name = cache_names(
            kind,
            name,
            start,
            end,
            args.cells,
            not args.no_land,
            args.sample_crs,
            args.resolution,
        )
        weather_cache = module.cache_path(weather_name)
        points_cache = module.cache_path(points_name)
        out_weather = args.out_dir / f"{weather_name}.parquet"

        if weather_cache.exists() and not args.refresh:
            print(
                f"{name:<10}{'-':>9}{'-':>10}{'-':>7}{'-':>7}{0:>9}  cached"
            )
            continue

        geometry, raw_km2, land_km2 = projected_geometry(
            module, kind, name, args, land
        )
        pool = sample_pool(
            geometry, args.pool, args.sample_crs, module.RANDOM_SEED
        )
        cells = grid_cells(pool)
        if not args.no_land:
            cells = cells_on_land(cells, land, args.sample_crs)
        chosen = choose_cells(cells, args.cells, module.RANDOM_SEED)

        weight = weighted_calls(len(chosen), start, end, module)

        if spent + weight > args.budget:
            print(
                f"{name:<10}{raw_km2:>9,.0f}{land_km2:>10,.0f}"
                f"{len(cells):>7}{len(chosen):>7}{weight:>9,.0f}  budget stop"
            )
            break

        if not args.dry_run:
            parts_dir = module.CACHE_DIR / "parts" / weather_name
            weather = fetch_hourly(
                chosen, start, end, parts_dir, module, refresh=args.refresh
            )
            daily_like = area_mean(weather, args.resolution, module)
            daily_like.reset_index().to_parquet(weather_cache, index=False)
            chosen.to_parquet(points_cache, index=False)
            args.out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(weather_cache, out_weather)

            manifest["entries"].append(
                {
                    "region": name,
                    "kind": kind,
                    "start": start,
                    "end": end,
                    "resolution": args.resolution,
                    "land": not args.no_land,
                    "sample_crs": args.sample_crs,
                    "pool_points": args.pool,
                    "available_cells": int(len(cells)),
                    "requested_cells": int(len(chosen)),
                    "weighted_calls": round(weight, 1),
                    "rows": int(len(daily_like)),
                    "raw_km2": round(raw_km2),
                    "land_km2": round(land_km2),
                    "weather_file": str(weather_cache.relative_to(REPO_ROOT)),
                    "points_file": str(points_cache.relative_to(REPO_ROOT)),
                    "downloaded_at": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                }
            )
            save_manifest(manifest_path, manifest)

        spent += weight
        planned += weight
        total_cells += len(chosen)
        total_available += len(cells)
        print(
            f"{name:<10}{raw_km2:>9,.0f}{land_km2:>10,.0f}"
            f"{len(cells):>7}{len(chosen):>7}{weight:>9,.0f}"
            f"  {'dry-run' if args.dry_run else 'downloaded'}"
        )

    print("-" * len(header))
    print(f"Requested grid cells: {total_cells:,} (available {total_available:,})")
    print(f"Planned weighted calls: {planned:,.0f} / budget {args.budget:,.0f}")
    if args.dry_run:
        print("Dry run: no ERA5 calls, no weather files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
