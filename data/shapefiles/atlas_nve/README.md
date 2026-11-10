# NVE Atlas area shapefiles (published dependency)

Source: <https://atlas.nve.no> — the official shapefile download for the two
layers the CA3 work needs. Extracted as-is from `Budområder.zip` and
`NVE_Region.zip`; nothing was edited. Committed here so the notebook and the
tests run from a fresh clone without touching the network.

| directory | ArcGIS layer | fields | features |
|---|---|---|---|
| `Budområder/` | `Nettomraader/MapServer/0` (`Budomraade`) | `budomr` = `NO 1`…`NO 5` | 5 |
| `NVE_Region/` | `Mapservices/Administrasjon2/MapServer/0` (`NVE_Region`) | `REGION` = `RS`, `RV`, `RØ`, `RM`, `RN` | 5 |

Both are ETRS89 / UTM 33N (EPSG:25833) and cover the same 470 107 km² — the same
country outline, partitioned two ways: electricity price areas and NVE's five
administrative regions. The regions group into the Magasinstatistik VASS areas
as East = RS + RØ, West = RV, North = RM + RN.

## Two things to know before using them

- **`NVE_Region.dbf` has no `.cpg` sidecar**, so GDAL assumes ISO-8859-1 and
  `REGION` for Region Øst arrives as `'RÃ\x98'` instead of `'RØ'`. Read it with
  `encoding="utf-8"` (as `read_area_shapefile()` does). Otherwise a filter for
  `{RS, RØ}` silently matches Region Sør alone — 74 686 km² instead of
  138 366 km² — with no error.
- **Field names are truncated** by the ArcGIS export: `st_area(sh` and
  `st_perimet` are `st_area(shape)` and `st_perimeter(shape)`, and the computed
  columns are empty. Only `budomr` / `REGION` are used here, so it does not
  matter; use the REST export if you need the full names.

Verified 2026-11-10 against the live services: identical feature counts,
identical `st_area` values, symmetric difference ≤ 0.0025 km² per area (the
EPSG:25833 → 4326 → 25833 round trip), and 1000 sampled points per area agree to
≤ 1 cm between this copy and the ArcGIS GeoJSON export.
