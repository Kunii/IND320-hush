# Coordinate reference systems — what we use, where, and why

Reference for anyone (human or agent) touching geometry in this repository.
Every CRS decision in the repo belongs to the CA3 work; the Streamlit app is
CRS-free by construction, because the projection happens before the numbers
reach it.

## The four rules

1. **Source data is EPSG:25833.** NVE serves both Atlas layers in ETRS89 /
   UTM 33N — it is in the `.prj` of the shapefiles and in `wkid: 25833` of the
   ArcGIS layers. Do not "normalise" it on import; do not assume 4326.
2. **Everything that crosses a boundary is EPSG:4326.** open-meteo takes WGS84
   lon/lat, GeoJSON is WGS84 by definition, and the notebook's figures and
   hand-in tables are in degrees.
3. **Anything that measures or samples uniformly per area is EPSG:3035.**
   LAEA Europe is equal-area, so a random point is equally likely per km².
4. **Never draw sample points in EPSG:4326.** Uniform in degrees is not uniform
   in km². See the measured bias below.

## Where each one is used

| CRS | Where | Why |
|---|---|---|
| **EPSG:25833**<br>ETRS89 / UTM 33N | `data/shapefiles/atlas_nve/*/*.prj`<br>`NVE_Region` and `Budomraader` ArcGIS layers<br>`tests/test_analysis.py::test_east_group_covers_south_and_east` | NVE's native CRS. Metres, so lengths and areas are meaningful and no resampling is introduced at import. Conformal, not equal-area: see the distortion note. |
| **EPSG:4326**<br>WGS84 lon/lat | `Proj-P3.py::read_area_shapefile` (returns 4326)<br>`Proj-P3.py::download_area_layer` (GeoJSON `outSR=4326`)<br>`Proj-P3.py::sample_area_points` (sampling space)<br>`Proj-P3.py::fetch_era5` (API coordinates)<br>notebook figures | What web APIs and GeoJSON speak. Degrees cross the wire, so no projection artefacts ship with the hand-in. |
| **EPSG:3035**<br>LAEA Europe | `precompute_weather.py::land_union`<br>`precompute_weather.py::projected_geometry`<br>`precompute_weather.py::sample_pool`<br>`precompute_weather.py::cells_on_land` | Equal-area. This is what makes the app's area means defensible: the 1000-point pool is uniform per km², and the land clip is computed in the same space. |
| **none** | `src/utils/*.py`, `src/streamlit/pages/*.py`, `streamlit_app.py` | The app reads area-keyed aggregates (`weather_<kind>_<area>_<range>_c<cells>_...parquet`). No coordinates, no CRS, nothing to project. |

## Why 25833 is right for source data and wrong for area sums

UTM 33N is conformal: it preserves shape and angles, and inflates area away from
the central meridian (15°E). Measured on this dataset (25833 ÷ 3035):

| area | ratio | area | ratio |
|---|---|---|---|
| NO1 | 1.0005 | East | 1.0022 |
| NO2 | 1.0040 | West | 1.0045 |
| NO3 | 1.0021 | North | 1.0009 |
| NO4 | 1.0010 | total | 470 107 / 469 244 km² (+0.18 %) |
| NO5 | 1.0040 | | |

So quoting "470 107 km²" is a UTM figure — fine for comparison between areas,
0.18 % high in absolute terms. Use 3035 when area shares or densities matter.

## Why sampling in degrees was a real bias

`Proj-P3.py::sample_area_points` samples uniformly in the GeoSeries' own CRS,
which is EPSG:4326 for the notebook. Density is therefore uniform per degree²,
not per km². Two identical 10° × 10° boxes demonstrate it: 60–70°N covers
521 922 km² and 70–80°N covers 319 319 km², and both receive the same 20 000
points (38.3 vs 62.6 points per 1000 km²).

In the areas that matter to the CA3 analysis, splitting each polygon at the
median sampled latitude:

| area | north half | south half | ratio |
|---|---|---|---|
| NO4 | 9.94 pts/1000 km² | 3.27 | 3.0× |
| NO3 | 20.70 pts/1000 km² | 6.26 | 3.3× |

Consequence: the notebook's NO3 series (the one behind SPC and LOF)
over-samples northern, higher, colder ground by about 3× in area terms, so it
should read slightly colder than the app's land-clipped EPSG:3035 series. The
two are different estimators by design, and both are documented as such.

`precompute_weather.py` does not have this problem — that is exactly what its
"Projected sampling" revision fixed.

## Related data trap (same family of bug)

`data/shapefiles/atlas_nve/NVE_Region/NVE_Region.dbf` has no `.cpg` sidecar, so
GDAL assumes ISO-8859-1 and `REGION` for Region Øst arrives as `'RÃ\x98'`.
A filter for `{RS, RØ}` then matches Region Sør alone — 74 686 km² instead of
138 366 km² — with no exception raised. Always read it with
`encoding="utf-8"`, and never filter on a group of codes without asserting that
every code was found.

## How to verify any of this

```bash
# source CRS
grep -o 'PROJCS\["[^"]*' data/shapefiles/atlas_nve/*/*.prj

# what the service says
curl -s 'https://kart.nve.no/enterprise/rest/services/Nettomraader/MapServer/0?f=json' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["extent"]["spatialReference"])'

# area under both projections
.venv/bin/python -c "
import geopandas as gpd
g = gpd.read_file('data/shapefiles/atlas_nve/Budområder/Budområder.shp')
for crs in (25833, 3035):
    print(crs, round(g.to_crs(crs).area.sum() / 1e6))
"
```

## If you change a CRS or a sampler

1. Update the cache key. `Proj-P3.py::area_sample_name` and
   `::weather_cache_name` do **not** encode the CRS, so a change would silently
   reuse stale points. `precompute_weather.py::cache_names` gets this right with
   its `_c100_land3035_hourly` suffix — follow that pattern.
2. Re-run the notebook (`nbconvert --execute --inplace`), then re-export the
   HTML, or the hand-in stops matching the code.
3. Update this file, the notebook's §4 markdown, and the module docstrings in the
   same change.
