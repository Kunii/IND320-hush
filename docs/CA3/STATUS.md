# CA3 Status — Data Quality

**Repository:** `Kunii/IND320` (private staging/development repo; `gh` confirms `isPrivate: true`)  
**Branch:** `main` (working directly on `main` is intentional here)  
**Repo state:** `main`, clean, in sync with `origin/main`  
**Last reviewed:** 2026-11-10 12:52 CET  
**Assignment deadline:** Tuesday **2026-11-10, 23:59 CET — today**  
**Task source:** [`docs/CA3/task.md`](task.md) (converted from the Canvas `.mht`)

> **Repo policy:** all CA3 work stays in this private staging repo. Do not push
> to the public `Kunii/IND320-hush` repo. The public hand-in repository/app is
> handled separately and is out of scope for this document.

---

## Contents

1. [Status at a glance](#1-status-at-a-glance)
2. [Requirement coverage](#2-requirement-coverage)
3. [Verification of earlier claims](#3-verification-of-earlier-claims)
4. [Defect register](#4-defect-register)
5. [Fixes applied](#5-fixes-applied)
6. [Outstanding work](#6-outstanding-work)
7. [Decisions](#7-decisions)
8. [Verification log](#8-verification-log)
9. [Key file map](#9-key-file-map)
10. [Reference notes](#10-reference-notes)

---

## 1. Status at a glance

The **analysis, notebook hand-in and both CA3 Streamlit pages are complete**;
the app is not yet deployed and the screencast is not recorded. With the
deadline at 23:59 tonight, the critical path is: test/deploy the app, record the
5-minute screencast, refresh the notebook log/links, then submit.

| Workstream | State | Notes |
|---|---|---|
| Assignment text conversion (`task.md`) | ✅ Done | All 73 content blocks from the `.mht` present |
| Analysis script (`Proj-P3.py`) | ✅ Working | 1062 lines; compiles; all four analyses run |
| Analysis self-tests | ✅ Done | 19/19 pass; re-run 2026-11-10 after the shapefile fix |
| Jupyter Notebook | ✅ Done | 56 cells (43 code), execution counts 1–43, zero errors, 7 figures; NO3 2024 retrieved hourly (8,784 rows) |
| PDF / HTML hand-in | ✅ Done | `Proj-P3.pdf` 32 pages (letter), `Proj-P3.html` 1.59 MB |
| Log + AI-usage section | ✅ Done | 482-word log body + AI note |
| ERA5 app caches | ✅ Done | 8 areas × 2024, hourly, land-clipped, 100 cells; 4,151.8 weighted calls; 1.18 MB in `data/precomputed/weather/` |
| CA3 Streamlit pages | ✅ Done | `reservoir_analysis.py` (STL \| Spectrogram) and `weather_quality.py` (SPC \| LOF); 2 tabs each |
| Streamlit deployment | ◐ P2 only | App asleep: HTTP 303 → `share.streamlit.io/-/auth/app` |
| Screencast | ❌ Missing | No video, no Panopto link |
| Commit / push | ✅ Done | latest CA3 commit on `main`, pushed to `origin/main` 2026-11-10 |
| Figures on disk | ◐ Notebook only | `data/output/ca3/` empty; notebook never calls `save_figure` |

**Bottom line:** the executed notebook, its PDF/HTML exports and the tests are
done and committed, the eight app weather caches are precomputed, and both CA3
Streamlit pages are built and render locally. The remaining submission blockers
are **deployment** and the **screencast**. The one analysis caveat is the SPC
series: the notebook runs it on temperature per the teacher's clarification
while the task text says precipitation; the app offers both. That choice is
documented in the notebook summary (§9) but remains the main examiner-risk item.

### Remaining actions

| Order | Action | Estimate |
|---|---|---|
| 1 | Test the pages against the deployed app, wake/deploy it | 1 h |
| 2 | Record the 5-minute screencast | 1 h |
| 3 | Update the notebook log/links, re-execute and re-export | 1 h |
| 4 | Submit the PDF and links | 30 min |

---

## 2. Requirement coverage

Legend: ✅ done · ◐ partial/needs work · ❌ missing · — out of scope by project decision

### 2.1 General / hand-in mechanics

| Requirement | Status | Evidence / gap |
|---|---|---|
| New GitHub branch for updates | — | Private staging repo; working on `main` is intentional |
| Jupyter Notebook run locally | ✅ | `notebooks/CA3/Proj-P3.ipynb`, executed end-to-end |
| Brief AI-usage description | ✅ | `## AI usage` in the notebook |
| 300–500 word log (notebook + Streamlit experience) | ✅ | 429 words of body text (431 including the heading) under `## Log` |
| Links to public GitHub repo + Streamlit app | ◐ | Both links present, but the repo is private and the app serves P2 |
| Clear navigable headings | ✅ | Numbered sections 1–9 match the assignment |
| Enough comments to be reproducible | ✅ | Code cells keep the script's comments |
| All code run before PDF export | ✅ | 43/43 code cells executed, zero errors |
| `.ipynb` added to the GitHub repo | ✅ | Committed as `e25c978` and pushed (private repo) |

### 2.2 Accounts / repositories / API

| Requirement | Status | Evidence / gap |
|---|---|---|
| Reuse account, repo and Streamlit app | — | Private staging repo by project decision |
| Push to a temporary branch | — | Same |
| Familiarise with open-meteo API | ✅ | `fetch_era5` uses `archive-api.open-meteo.com`, `models=era5`, hourly temp + precipitation |

### 2.3 Jupyter Notebook tasks

| Requirement | Status | Evidence / gap |
|---|---|---|
| NVE Atlas electricity + precipitation layers, East=RS+RØ, North=RM+RN | ✅ | `download_area_layer`, `PRECIPITATION_GROUPS`; both REST layers downloaded and verified |
| Download official shapefiles from atlas.nve.no | ◐ | Uses the equivalent ArcGIS REST GeoJSON (documented in the notebook); local shapefiles in `data/shapefiles/` take priority |
| Randomly sample 1000 locations in each region | ✅ | Verified at 1000 points for NO1–NO5 and East/West/North (notebook cell 28) |
| ERA5 **hourly** reanalysis | ✅ | NO3 2024: 8,784 hourly area means from 1000 points via `download_region_weather(..., resolution="hourly")`; a separate one-coordinate demo is not shown |
| Function taking region id + time interval, looks up lon/lat pairs, downloads precip + temp | ✅ | `download_region_weather(region_id, start_date, end_date, ...)` |
| Apply the function to NO3 for 2024 | ✅ | Hourly: **8,784 rows**, `point_count=1000`; daily 366 rows derived for SPC/LOF |
| Plot average precipitation vs time | ✅ | `run_weather_analysis` produces `precipitation_*.png`; notebook cell 40 plots it inline |
| DCT high-pass of precipitation → SATV | ◐ | Runs on **temperature** per the teacher clarification; precipitation is only downloaded/plotted |
| SPC bounds from robust statistics, colour outliers, don't plot SATV | ✅ | Default ±2σ flags 12/366 days on NO3 2024 |
| DCT cutoff + std-dev parameters with sensible defaults | ✅ | `DCT_CUTOFF_FRACTION=0.02`, `SPC_STD_DEVIATIONS=2.0` |
| Wrap SPC in function returning plot + summary, and test | ✅ | `spc_outliers` + `test_spc_flags_injected_spike` |
| Plot average temperature vs time | ✅ | Produced inside the LOF figure |
| LOF anomalies, contamination default 1% | ✅ | `LOF_CONTAMINATION=0.01`; verified 4/366 ≈ 1% |
| Wrap LOF in function returning plot + summary, and test | ✅ | `lof_outliers` + `test_lof_flags_about_contamination` |
| STL on degree of filling, plot decomposition | ✅ | Verified on 1,661 weekly observations |
| STL seasonal/trend/robust parameters + defaults | ✅ | `13`, `101`, `True` |
| Wrap STL in function returning plot, and test | ✅ | `stl_analysis` + reconstruction/validation tests |
| Spectrogram on same data | ✅ | Verified on the real filling series |
| Window/overlap parameters + defaults | ✅ | `52` / `26` weeks |
| Wrap spectrogram in function returning plot, and test | ✅ | `spectrogram_analysis` + shape test |
| Log + AI section | ✅ | `## Log` (429/431 words) and `## AI usage` |

### 2.4 Streamlit app tasks

| Requirement | Status | Evidence / gap |
|---|---|---|
| Update the P2 app | ✅ | Two new pages plus reordered navigation; P2 pages retained |
| Weather download follows the magasinstatistikk selector | ✅ | Local selector maps EL 1–5 → NO1–NO5 and VASS 1–3 → East/West/North; data served from the precomputed caches |
| Download control/confirmation page or hidden integrated control | ✅ | Integrated and hidden: the page caption confirms area, year, rows and grid cells; no runtime API calls |
| New page: `st.tabs()` → STL \| Spectrogram | ✅ | `src/streamlit/pages/reservoir_analysis.py` |
| New page: `st.tabs()` → Outlier/SPC \| Anomaly/LOF | ✅ | `src/streamlit/pages/weather_quality.py` |
| Reorder pages logically | ✅ | Home → table → plot → reservoir analysis → weather quality → flows |

### 2.5 Screencast / evaluation

| Requirement | Status | Evidence / gap |
|---|---|---|
| 5-minute screencast | ❌ | No `Proj-P3.mp4` or Panopto link |
| PDF ready for upload | ◐ | `notebooks/CA3/Proj-P3.pdf` (31 pages) produced; Canvas upload still pending |
| GitHub repository | ◐ | Exists; private staging repo |
| Streamlit app | ◐ | P2 app only; asleep on Streamlit Cloud |
| Screencast | ❌ | None |

---

## 3. Verification of earlier claims

`HANDOFF.md` was the pre-audit handoff and was **retired on 2026-11-10**; its
durable reference facts live in [§10](#10-reference-notes). This table keeps the
audit trail of what it claimed versus what was checked.

| Earlier claim | Verdict | Evidence |
|---|---|---|
| `task.md` is a complete conversion of the `Detaljer` expander | ✅ **True** | All **73/73** content blocks from the `.mht` appear after normalising links/markdown. The "67 sentences" count differs, but content coverage is complete |
| `Proj-P3.py` is a working script covering the assignment sections | ✅ **Largely true** | Compiles; imports; all four analyses run; both NVE layers download; 1000-point sampling works for all 8 regions; ERA5 download works; end-to-end NO3 run completes |
| `.venv` synced; pandas 3.0.3, streamlit 1.63.0, geopandas 1.2.0, shapely 2.2.0 | ✅ **True** | Also statsmodels 0.15.0, sklearn 1.9.1, scipy 1.18.1 |
| `.secrets/secrets.toml` has mongo + entsoe keys | ✅ **True** | Keys present; values not read |
| Nothing committed since the import commit | ✅ **True at audit time** | On 2026-11-09 `main` was at `8bd8eea` and the CA3 work was uncommitted. Superseded on 2026-11-10 by commit `e25c978` |
| `uv.lock` is consistent | ✅ **True** | `uv lock --check` resolves cleanly |
| Helpers return `(figure, summary)` for reuse | ✅ **True** | Confirmed in STL, spectrogram, SPC and LOF |
| Caches go to `data/cache`, figures to `data/output/ca3` | ◐ **Partly true** | Caches confirmed; `data/output/ca3/` is empty because the notebook does not call `save_figure`. Figures are embedded in the notebook/HTML/PDF |
| SPC limits are deliberately time-varying | ✅ **True** | Baseline from the DCT low-pass, width from the robust σ of the high-pass |

Things the earlier handoff did **not** capture, now fixed:

- The weather cache ignored the point count (D1).
- The SPC default produced zero outliers (D2).
- The spectrogram axis was misleading (D3).
- There was no function with the assignment's exact "region id + interval" shape (D4).
- The points cache was written but never read (D5).
- There were no tests (D6).
- The README was stale (D8).
- `scipy` was an undeclared direct dependency (D9).

---

## 4. Defect register

Status values: **FIXED** (2026-11-09) · **OPEN** · **DEFERRED** (project decision)

| ID | Severity | Defect | Status |
|---|---|---|---|
| D1 | High | Weather cache filename ignored `count`; a 24-point smoke test was silently reused as the 1000-point result | **FIXED** |
| D2 | High | SPC default ±3σ flagged **zero** days on NO3 2024 temperature, so no outliers were coloured | **FIXED** |
| D3 | Medium | Spectrogram plotted the full 0–0.5 cycles/week range, squashing the annual cycle; x-label said "segment index" but showed weeks | **FIXED** |
| D4 | Medium | No function matched the assignment's "region identifier + time interval" signature | **FIXED** |
| D5 | Low | Sampled-points cache was written but never read | **FIXED** |
| D6 | High | No tests for the four analysis functions | **FIXED** |
| D7 | — | Private repo / public-repo mismatch and branch requirement | **DEFERRED** — private staging repo by project decision; public repo out of scope |
| D8 | Low | README stale: referenced deleted `reservoirs.csv`, missing `.github/`, no CA3 section | **FIXED** |
| D9 | Low | `scipy` imported directly but not declared in `pyproject.toml` | **FIXED** |
| D10 | Low | `run_weather_analysis` precipitation title used the global `WEATHER_YEAR` instead of the actual `year` argument | **FIXED** |

### D1 — cache key collision (detail)

Before:

```python
cache = cache_path(f"weather_{kind}_{name}_{year}")
```

The filename omitted `count`. Demonstrated by running `count=24` and then
`count=1000`; the second call returned `point_count = 24`.

After: the filename is
`weather_{kind}_{name}_{start}_{end}_{count}.parquet`, so
`weather_electricity_NO3_2024-01-01_2024-12-31_24.parquet` and
`..._1000.parquet` are distinct.

### D2 — zero outliers (detail)

The SATV residual for daily NO3 2024 temperature has robust σ ≈ 3.25 °C and
max |SATV − median| ≈ 9.5 °C ≈ 2.9σ. At ±3σ the outlier set is empty; at ±2σ
it contains 12 days (≈3.3%). The parameter remains adjustable; the default is
now 2σ so the SPC plot actually demonstrates the requirement.

### D3 — spectrogram (detail)

Before: `ax.set_xlabel("Segment index [weeks]")` with `times` in sample
positions (0–1661) and a 0–0.5 y-range. After: dates on the x-axis and a
0–0.1 cycles/week y-range (the band containing the annual and semi-annual
cycles); the full range is still available via `max_frequency=None`.

### D7 — repo policy (deferred)

The assignment asks for a public repository and a temporary branch. This
project deliberately uses the private staging repo `Kunii/IND320` and works on
`main`; the public `Kunii/IND320-hush` repo is explicitly out of scope. Record
the public-repo/branch story at submission time.

---

## 5. Fixes applied

All changes from the 2026-11-09 pass are committed in `e25c978` (2026-11-10).

### 5.1 `notebooks/CA3/Proj-P3.py`

| Change | Location | What it does |
|---|---|---|
| SPC default ±2σ | `SPC_STD_DEVIATIONS` (~line 159) | Produces a visible outlier set; documented rationale |
| Spectrogram date axis + zoom | `spectrogram_analysis` (~line 314) | Maps segment positions to dates, zooms to 0–0.1 cycles/week, adds `max_frequency` |
| Region inference | `region_kind` (~line 491) | `"NO3"` → electricity, `"East"` → precipitation |
| Cache key includes count | `weather_cache_name` (~line 510) | `weather_{kind}_{name}_{start}_{end}_{count}` |
| New download function | `download_region_weather` (~line 834) | Region id + start/end dates + optional kind/count/refresh; reads and writes both caches |
| Pipeline uses the new function | `run_weather_analysis` (~line 902) | Adds a `year` parameter; precipitation title uses the actual year |

The script is 975 lines at last review (it was 876 lines before the 2026-11-09
fixes).

### 5.2 New `notebooks/CA3/test_proj_p3.py`

15 plain-assert tests, runnable with or without pytest:

```bash
.venv/bin/python notebooks/CA3/test_proj_p3.py
# 15/15 tests passed
```

Covered: robust sigma, code normalisation, region inference, area codes,
cache-name uniqueness, `filling_series`, STL reconstruction and parameter
validation, spectrogram shapes, SATV constant/annual-cycle removal, SPC spike
detection, LOF contamination, `area_mean` aggregation, and reversed-date
validation.

### 5.3 `README.md`

Rewritten for the current repo: project-parts table, CA3 files, cache/quota
notes, local run commands, and a pointer to this document. Removed references
to the deleted `reservoirs.csv`, the missing `.github/` directory and the
non-existent `src/streamlit/components/`.

### 5.4 `pyproject.toml` / `uv.lock`

Added `scipy` as a direct dependency; `uv lock` refreshed the lock (183
packages, consistent).

### 5.5 `HANDOFF.md` — retired (2026-11-10)

The pre-audit handoff was obsolete: its status sections duplicated this
document and its "next steps" were already done. The still-useful reference
material — Magasinstatistikk codes, the NVE Atlas endpoints, the open-meteo
quota/batching notes and the environment gotchas — was moved to
[§10](#10-reference-notes), and `HANDOFF.md` was deleted. A copy of the deleted
file is kept outside the repo at
`~/.hermes/profiles/ind320/cache/scratch/HANDOFF.md.bak`.

### 5.6 Notebook delivery (2026-11-09, refreshed 2026-11-10)

`notebooks/CA3/Proj-P3.ipynb` was generated from the tested script with
`nbformat`/`ast`, given the required markdown sections, and executed with the
project kernel:

- 56 cells (43 code cells), all executed; execution counts 1–43; **zero cell
  errors**; 7 embedded figures.
- 1000-point NO3 2024 download: **8,784 hourly area means**,
  `point_count = 1000`; the analysis derives 366 daily means from them.
  The original daily run hit one `HTTP 429` at 944/1000 (1220 s wait); the
  hourly re-run hit one at 960/1000 (1348 s wait). Both were handled by the
  retry and are kept as evidence of the rate-limit handling.
- Aggregating the hourly cache to daily reproduces the earlier daily cache
  exactly (maximum absolute difference 0.000000 for temperature and
  precipitation), so the SPC/LOF results are unchanged.
- SPC: **12/366** days flagged at ±2σ (3.3%); LOF: **4/366** at 1%
  contamination.
- All 8 regions sampled with 1000 points; the sampling table is in the
  notebook (cell 28).
- Tests: 15/15 in the notebook and in the standalone module.
- Exports: `Proj-P3.html` (1.6 MB, embedded plots) and `Proj-P3.pdf`
  (29 pages, letter portrait). The PDF was produced with headless Chromium
  from the HTML, per the notebook-hand-in workflow.

| File | Size |
|---|---|
| `notebooks/CA3/Proj-P3.ipynb` | 1.2 MB |
| `notebooks/CA3/Proj-P3.html` | 1.6 MB |
| `notebooks/CA3/Proj-P3.pdf` | 2.0 MB |

The notebook is a snapshot of `Proj-P3.py`; if the script changes, regenerate
and re-execute rather than editing both by hand. The notebook defines
`save_figure` but never calls it, so **no PNG files are written** to
`data/output/ca3/`; the figures exist only inside the notebook and its exports.

### 5.7 ERA5 precompute for the app (2026-11-10)

`notebooks/CA3/precompute_weather.py` downloaded land-clipped hourly ERA5
caches for all eight areas for 2024:

- Sampling: 1000 points per area in EPSG:3035, clipped to NVE's land layer
  (`Norge_N5000`, `OBJTYPE != 'Havflate'`); points snapped to 0.25° ERA5 cells,
  sea cell centres removed, 100 cells chosen per area (94 for NO5).
- Download: 794 cells in total, **4,151.8 weighted calls** (under the 4,800
  budget and the 5,000/hour limit); no 429.
- Output: 8,784 hourly rows per area (70,272 rows in total), 1.18 MB of
  parquet in `data/precomputed/weather/` plus a manifest. Each batch was
  checkpointed under `data/cache/parts/`.

The app cache is deliberately **not** the same series as the notebook: the
notebook keeps its original unclipped daily NO3 2024 cache (1000 points) for
the executed hand-in, while the app data is land-clipped and hourly. On NO3
2024 the land-clipped daily mean is 1.6 °C colder (5.65 → 4.05 °C, daily
correlation 0.998); hourly SPC at 3σ with a 12-cycle/year cutoff flags
13/8784 hours (0.15 %), which validates the 3σ default on the new resolution.

### 5.8 CA3 Streamlit pages (2026-11-10)

- `src/ca3/analysis.py` — app-side STL, spectrogram, SPC and LOF helpers.
- `src/ca3/data.py` — `filling_series` (Magasinstatistikk) and `weather_frame`
  (precomputed ERA5).
- `src/streamlit/pages/reservoir_analysis.py` — `st.tabs()` STL | Spectrogram,
  local area selector, parameter sliders and metrics.
- `src/streamlit/pages/weather_quality.py` — `st.tabs()` Outlier/SPC |
  Anomaly/LOF, area selector mapped to the eight cached areas, temperature/
  precipitation choice, contamination/neighbours, metrics and outlier tables.
- `streamlit_app.py` — page order Home → table → plot → reservoir analysis →
  weather quality → flows.

Verification: `py_compile` passes; `streamlit.testing.v1.AppTest` runs both
pages (including VASS and East/precipitation variants) with zero exceptions;
the local server returns HTTP 200 and the sidebar shows all six pages. Default
NO3 results: SPC **14 outliers (0.16 %)** at 12 cycles/year and 3σ; LOF
**88 anomalies (1.00 %)**.

### 5.9 Official Atlas shapefiles as the primary area source (2026-11-10)

The shapefiles downloaded from atlas.nve.no are now the primary source for the
two NVE Atlas layers; the ArcGIS GeoJSON export stays as the fallback.

- **Published dependency:** `data/shapefiles/atlas_nve/Budområder/` and
  `data/shapefiles/atlas_nve/NVE_Region/` (8 files, ~1.4 MB, committed).
  `.gitignore` was `data/shapefiles/`, which would have hidden them, so it now
  ignores `data/shapefiles/*` and re-includes `!data/shapefiles/atlas_nve/`.
- **Private raw dump:** `data/atlas_nve/` (the two zips, `atlas.nve-dl.json`
  and the derived `inventory/`) is gitignored.
- The loader tries the committed copy, then the raw dump, then the cached
  GeoJSON, then a live download.

Both routes address the same layers: identical feature counts, identical
`st_area(shape)` values, symmetric difference ≤ 0.0025 km² per area (the
25833 → 4326 → 25833 round trip), and the 1000 sampled locations per area agree
to ≤ 1 cm either way.

Switching exposed a real defect in the local-shapefile branch:

- `NVE_Region.dbf` has no `.cpg`, so `gpd.read_file()` read it as ISO-8859-1 and
  `REGION` for Region Øst arrived as `'RÃ\x98'`. `East = ("RS", "RØ")` then
  matched Region Sør alone — **74 686 km² instead of 138 366 km²** — with no
  exception raised, because `matches.any()` was satisfied by the RS row.
- Fixes: `read_area_shapefile()` reads UTF-8 (falling back to the GDAL default
  only on `UnicodeDecodeError`); `select_area_geometry()` now requires *every*
  code in a group and raises listing the missing ones; `resolve_service_layer_id()`
  looks the ArcGIS layer up by name, because NVE republishes services and ids
  move (`Administrasjon2/MapServer` has already been reordered).
- Tests: 19/19 (4 new) — missing-code and mojibake-code rejection, UTF-8 region
  codes, and East ≈ 138 366 km².
- Notebook re-executed (43 code cells, 1–43, zero errors, 7 figures) and the
  exports rebuilt: `Proj-P3.html` 1.59 MB, `Proj-P3.pdf` 32 pages letter.
  Results are unchanged — the sampling polygons are identical — so the ERA5
  caches and every SPC/LOF number stay valid.

### 5.10 CRS documented where it is used (2026-11-10)

CRS choices were correct but implicit. They are now stated at each layer:

- `docs/crs.md` — the reference: four rules, a table of what/where/why with
  function anchors, the measured UTM distortion (0.05–0.45 %), the measured
  degree-sampling bias (NO4 3.0×, NO3 3.3× north-vs-south density), the
  `NVE_Region` encoding trap, verification commands, and a change checklist
  (including the cache-key trap: `area_sample_name`/`weather_cache_name` do not
  encode the CRS).
- Notebook §4 — a "Coordinate reference systems" subsection with the three-CRS
  table and the sampler caveat, in the markdown the examiner reads.
- Docstrings — `Proj-P3.py` module + `read_area_shapefile`,
  `download_area_layer`, `sample_area_points`, `fetch_era5`;
  `precompute_weather.py` module + `land_union`, `projected_geometry`,
  `sample_pool`, `grid_cells`, `cells_on_land`; the area regression test.
- App — `src/ca3/data.py`, `src/ca3/analysis.py`, `streamlit_app.py` and both
  CA3 pages now state explicitly that they carry no geometry, so a future
  change knows the projection is deliberately upstream.

No code path changed: `py_compile` passes, tests 19/19, both pages render with
`AppTest` and zero exceptions, notebook re-exported (32 pages, 1.59 MB HTML).

---

## 6. Outstanding work

Ordered for a same-day finish.

### P0 — submission blockers

1. **Deploy / wake the app** and test the online version with the two new pages.
   Both `ind320-hush.streamlit.app` and `ind320-hush-p2.streamlit.app` currently
   answer `303 → share.streamlit.io/-/auth/app` (asleep).
2. **Record the 5-minute screencast** and store or link it (Panopto link in the
   notebook or a video file in the repo).

### P1 — quality and correctness

3. Update the notebook's `## Log` Streamlit paragraph. It is currently written
   in the future tense ("the CA3 pages will reuse that structure"); the pages
   now exist, so describe what was actually built, then re-execute and re-export
   the notebook/PDF.
4. Update the notebook title cell with the public repo/app links and upload the
   PDF/HTML at submission time; re-export after any notebook edit.

### P2 — nice to have

5. Use official NVE shapefiles in `data/shapefiles/` if `nedlasting.nve.no`
   comes back.
6. Add more ERA5 variables (humidity, wind) if quota allows.

---

## 7. Decisions

| Decision | Status | Choice / recommendation |
|---|---|---|
| SPC series | **Decided** | Temperature, per the teacher's clarification; documented in notebook §9. Precipitation is still downloaded and plotted. Revisit only if the clarification is withdrawn |
| SPC default | **Decided** | Notebook: 2σ on the daily series; app: 3σ on the hourly series with a 12-cycle/year cutoff. Both are documented in the pages |
| App point count | **Decided** | 100 land-clipped ERA5 cells per area, hourly, precomputed for 2024; the app reads the cache. The notebook keeps its 1000-point NO3 series |
| App weather source | **Decided** | Serve `data/precomputed/weather/` from the repo; no open-meteo calls at runtime |
| App plot library | **Decided** | Matplotlib helpers rendered with `st.pyplot`, matching the tested notebook functions |
| Public repo/app | **Open** | Out of scope for this staging repo; handle at submission time |
| Commit target | **Decided** | Committed on `main` (staging policy); latest CA3 commit pushed 2026-11-10 |

---

## 8. Verification log

Commands actually run and their results. First block: 2026-11-09 audit. Second
block: 2026-11-10 re-check.

```text
$ .venv/bin/python -m py_compile notebooks/CA3/Proj-P3.py
COMPILE OK

$ .venv/bin/python notebooks/CA3/test_proj_p3.py
15/15 tests passed

$ .venv/bin/python -m nbconvert --to notebook --execute --inplace \
    notebooks/CA3/Proj-P3.ipynb --ExecutePreprocessor.timeout=3600
43/43 code cells executed, 0 errors
1,000/1,000 locations downloaded, 366 daily rows
SPC (NO3 2024, 1000 points, 2σ): 12 outliers
LOF (NO3 2024, 1000 points, 1%): 4 anomalies

$ .venv/bin/python -m nbconvert --to html --embed-images \
    notebooks/CA3/Proj-P3.ipynb --output-dir notebooks/CA3 --output Proj-P3.html
Proj-P3.html (1.6 MB, embedded plots)

$ chromium --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
    --print-to-pdf=Proj-P3.pdf file://.../Proj-P3.html
Proj-P3.pdf (31 pages, letter portrait)
```

2026-11-10 re-check:

```text
$ .venv/bin/python notebooks/CA3/test_proj_p3.py
15/15 tests passed

$ python (nbformat check on Proj-P3.ipynb)
56 cells, 43 code, execution_count 1..43, 0 error outputs, 7 figures

$ pdfinfo notebooks/CA3/Proj-P3.pdf
Pages: 31
Page size: 612 x 792 pts (letter)

$ curl -s -D - -o /dev/null https://ind320-hush.streamlit.app
HTTP/2 303
location: https://share.streamlit.io/-/auth/app?redirect_uri=...

$ curl -s -D - -o /dev/null https://ind320-hush-p2.streamlit.app
HTTP/2 303 (same auth redirect)

$ gh repo view Kunii/IND320 --json isPrivate,pushedAt
{"isPrivate":true,"pushedAt":"2026-11-06T00:29:34Z"}
```

Commit and push (2026-11-10):

```text
$ git commit -m "Add CA3 data-quality analysis and hand-in"
[main e25c978] Add CA3 data-quality analysis and hand-in
 12 files changed, 28016 insertions(+), 44 deletions(-)

$ git push origin main
To github.com:Kunii/IND320.git
   8bd8eea..e25c978  main -> main

$ gh api repos/Kunii/IND320/commits/main --jq '.sha[0:7]'
e25c978
```

ERA5 precompute for the app (2026-11-10):

```text
$ .venv/bin/python notebooks/CA3/precompute_weather.py --year 2024 --cells 100
[8 areas: land-clipped, 100 cells each except NO5=94]
Requested grid cells: 794 (available 1,759)
Planned weighted calls: 4,151 / budget 4,800
[exit 0; no 429]

$ python (verification of the 8 caches)
8 × 8,784 hourly rows = 70,272 rows, 1.18 MB
no NaNs, no duplicate timestamps, point_count 100 (NO5 94)
```

Hourly NO3 2024 retrieval (2026-11-10):

```text
$ python download_no3_hourly.py
1000/1000 downloaded (429 at 960/1000, waited 1348 s)
8,784,000 per-location rows -> 8,784 hourly area means
point_count = 1000; no NaNs, no duplicate timestamps
daily aggregation matches the existing daily cache (max abs diff 0.000000)

$ python -m nbconvert --to notebook --execute --inplace \
    notebooks/CA3/Proj-P3.ipynb --ExecutePreprocessor.timeout=3600
43/43 code cells executed, 0 errors
Hourly rows: 8,784; Daily rows: 366
SPC 12/366; LOF 4/366; tests 15/15
Proj-P3.pdf: 29 pages (letter)
```

Streamlit pages (2026-11-10):

```text
$ .venv/bin/python -m py_compile src/ca3/analysis.py src/ca3/data.py \
    src/streamlit/pages/reservoir_analysis.py \
    src/streamlit/pages/weather_quality.py streamlit_app.py
COMPILE OK

$ python (streamlit.testing.v1.AppTest)
reservoir analysis: tabs ['STL', 'Spectrogram'], 0 exceptions
reservoir analysis / VASS: 0 exceptions
weather quality: tabs ['Outlier / SPC', 'Anomaly / LOF'], 0 exceptions
weather quality / East / precipitation: 0 exceptions

$ streamlit run streamlit_app.py --server.port 8502
HTTP 200; sidebar: Home, Reservoir table, Reservoir plot,
Reservoir analysis, Weather quality, Cross-border flows
```

Additional checks:

- `uv lock --check` — consistent, 183 packages.
- Streamlit app starts locally (HTTP 200); all four P2 pages render without
  errors.
- Repo state: `main` clean and in sync with `origin/main` after each CA3 commit.
- NVE data: 14,949 rows, 1,661 weekly observations per series, 1995-01-08 to
  2026-11-01.
- Electricity area sizes: NO1 60.5k km², NO2 68.8k, NO3 104.2k, NO4 203.3k,
  NO5 33.3k (raw polygons; land-clipped sizes are in §5.7).
- Notebook cache: `magasinstatistikk.parquet` (615 KB), both area GeoJSONs,
  `points_electricity_NO3_1000.parquet`, and the original daily
  `weather_electricity_NO3_2024-01-01_2024-12-31_1000.parquet`.
- App cache: 8 hourly land-clipped caches under `data/precomputed/weather/`
  (794 cells, 70,272 rows), plus `weather_manifest.json`.
- `data/output/ca3/` exists but is empty.

---

## 9. Key file map

| Path | Purpose |
|---|---|
| `docs/CA3/task.md` | Converted assignment text |
| `docs/CA3/STATUS.md` | This document — the single source of truth for CA3 |
| `docs/CA3/Project work, part 3 - Data quality.mht` | Original Canvas page |
| `notebooks/CA3/Proj-P3.py` | Working analysis script (STL, spectrogram, NVE areas, ERA5, SPC, LOF) |
| `notebooks/CA3/Proj-P3.ipynb` | Executed hand-in notebook (56 cells, outputs embedded) |
| `notebooks/CA3/Proj-P3.html` | Self-contained HTML export (embedded plots) |
| `notebooks/CA3/Proj-P3.pdf` | PDF hand-in export (31 pages) |
| `notebooks/CA3/test_proj_p3.py` | Self-tests for the analysis helpers |
| `notebooks/CA3/precompute_weather.py` | Land-clipped hourly ERA5 precompute for the app |
| `docs/CA3/peer-review-notes.md` | Review of three peer notebooks and design implications |
| `src/utils/magasin.py` | NVE Magasinstatistikk API + parquet cache |
| `src/utils/mongo.py` | MongoDB access for the flows page |
| `src/utils/env.py` | Secret loader (`.secrets` or `st.secrets`) |
| `src/ca3/analysis.py` | App-side STL, spectrogram, SPC and LOF helpers |
| `src/ca3/data.py` | Reservoir series and precomputed weather access |
| `src/streamlit/pages/reservoir_analysis.py` | CA3 page: STL \| Spectrogram tabs |
| `src/streamlit/pages/weather_quality.py` | CA3 page: SPC \| LOF tabs |
| `src/streamlit/pages/` | P2 pages plus the two CA3 analysis pages |
| `streamlit_app.py` | App entry point and six-page navigation |
| `data/cache/` | Generated parquet/GeoJSON caches (gitignored) |
| `data/precomputed/weather/` | Committable app ERA5 caches + manifest |
| `data/output/ca3/` | Intended CA3 figure output (gitignored; currently empty) |

---

## 10. Reference notes

Durable facts recovered from the retired `HANDOFF.md`; do not re-derive them.

**Provenance:** the repo content was imported from `../IND320-hush` (branch
`work-p3`, commit `a7529d6`) in commit `8bd8eea` ("Import IND320-hush work-p3
content"). CA3 keeps `Proj-P3.py` as the working script and generates the
hand-in notebook from it.

### 10.1 Magasinstatistikk codes

API:
`https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData`

- `EL` 1–5 = electricity price areas NO1–NO5
- `NO` 0 = whole country
- `VASS` 1–3 = three reservoir regions:
  1. Austlandet, Agder and parts of Rogaland
  2. rest of Rogaland and most of Vestland
  3. Møre og Romsdal, Trøndelag and Nord-Norge
- 14,949 rows, 1,661 ISO weeks per series, 1995-01-08 → 2026-11-01.

### 10.2 NVE Atlas layers

| Assignment term | NVE layer | ArcGIS REST | Field | Values |
|---|---|---|---|---|
| electricity areas | `Budomraade` | `https://kart.nve.no/enterprise/rest/services/Nettomraader/MapServer/0` | `budomr` | `"NO 1"`…`"NO 5"` (space included) |
| precipitation areas | `NVE_Region` | `https://kart.nve.no/enterprise/rest/services/Mapservices/Administrasjon2/MapServer/0` | `REGION` / `REGIONNAVN` | `RV`, `RM`, `RN`, `RØ`, `RS` |

- The "precipitation areas" are **NVE administrative regions**, not hydrological
  catchments. Grouping used by the assignment:
  `VASS1 = RS + RØ` (East), `VASS2 = RV` (West), `VASS3 = RM + RN` (North).
- Both layers are **EPSG:25833** (ETRS89 / UTM 33N). The script requests
  `outSR=4326` and calls `.to_crs("EPSG:4326")`.
- `nedlasting.nve.no/gis/` (the Atlas download page) is intermittently **out of
  service**. The script downloads GeoJSON from the REST endpoint and caches it;
  official shapefiles in `data/shapefiles/budomraader.shp` /
  `data/shapefiles/nve_regioner.shp` take priority when present.

### 10.3 open-meteo / ERA5

- Endpoint: `https://archive-api.open-meteo.com/v1/archive`, `models=era5`,
  `timezone=UTC`, hourly `temperature_2m,precipitation`.
- Free-tier limits are weighted by `locations × variables`; large coordinate
  lists trigger **HTTP 429**. `_request_with_retry` handles backoff/`Retry-After`,
  and the batch size (8) + 4 s pause are tuned to stay under the limit
  (10,000 weighted calls/day).
- Approximate cost: 1000 locations × 2 variables ≈ 2000 weighted calls per
  area-year. Check the daily budget before downloading all eight areas.
- Responses are snapped to the ERA5 grid, so sampled coordinates can collide;
  the area mean is therefore a plain mean over returned locations
  (`point_count` records coverage).

### 10.4 Environment gotchas

- **Do not put `src/` on `sys.path`.** `src/streamlit/` is a package and would
  shadow the real `streamlit`, breaking `st.cache_data` (`AttributeError`).
- Importing `src.utils.magasin` emits
  `WARNING streamlit.runtime.caching.cache_data_api: No runtime found` when run
  outside Streamlit. Harmless.
- Run the script from the repo root so `from src.utils.magasin import ...`
  resolves.
- `.gitignore` covers `data/cache/`, `data/output/`, `data/shapefiles/`;
  `__pycache__/` was already covered.
- pandas is 3.x — avoid removed/renamed APIs from 2.x tutorials.
- `statsmodels` STL requires odd `seasonal` and odd `trend > period`;
  `stl_analysis` validates this and raises readable errors.
- SPC limits are deliberately **time-varying** (baseline from the low-pass part
  of the DCT plus robust σ of the high-pass part). Flat limits flag every
  winter day.
- A 1000-point download can stall for ~20 minutes on a `429` retry; reuse the
  parquet cache for reruns instead of forcing `refresh=True`.

### 10.5 Reproduce

```bash
cd /mnt/nvme_storage/projects/NMBU/IND320
.venv/bin/python -m py_compile notebooks/CA3/Proj-P3.py
.venv/bin/python notebooks/CA3/test_proj_p3.py
.venv/bin/python notebooks/CA3/Proj-P3.py        # full pipeline, uses caches
```

Cheap layer + weather smoke check (no full download):

```bash
MPLBACKEND=Agg .venv/bin/python - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("p", "notebooks/CA3/Proj-P3.py")
m = importlib.util.module_from_spec(spec); sys.modules["p"] = m
spec.loader.exec_module(m)

# layers + sampling
for kind, name in [("electricity", "NO3"), ("precipitation", "East")]:
    areas = m.download_area_layer(kind)
    pts = m.sample_area_points(m.select_area_geometry(areas, kind, name), count=25)
    print(kind, name, len(pts))

# end-to-end weather run on 24 points (~6 requests)
m.run_weather_analysis(names=("NO3",), count=24, refresh=True)
PY
```

---

*Last reviewed 2026-11-10. This document is the single source of truth for CA3;
update it as the Streamlit pages, deployment and screencast are completed.*
