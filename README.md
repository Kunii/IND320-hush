# IND320 Project - RTE

## Streamlit app

[Main](https://ind320-hush.streamlit.app)  
[P2 Snapshot](https://ind320-hush-p2.streamlit.app)

## Project parts

| Part | Topic | Notebook / script | Task text |
|---|---|---|---|
| CA1 | Data sources and first Streamlit app | `notebooks/CA1/Proj-P1.ipynb` | `docs/CA1/task.md` |
| CA2 | Cassandra, MongoDB and ENTSO-E flows | `notebooks/CA2/Proj-P2.ipynb` | `docs/CA2/task.md` |
| CA3 | Data quality: STL, spectrogram, SPC and LOF | `notebooks/CA3/Proj-P3.ipynb` (+ `Proj-P3.py` script) | `docs/CA3/task.md` |

CA3 starts from [`docs/CA3/task.md`](docs/CA3/task.md).  
Coordinate handling is documented in [`docs/CA3/crs.md`](docs/CA3/crs.md).

## Repository structure

```txt
├── data/
│   ├── Y_eicCodes.csv          # ENTSO-E area codes
│   ├── cache/                  # generated parquet/GeoJSON caches (gitignored)
│   ├── precomputed/weather/    # shipped ERA5 area caches, both sources
│   └── shapefiles/atlas_nve/   # official NVE Atlas shapefiles (committed)
│
├── docs/
│   ├── CA1/                    # P1 task text and video
│   ├── CA2/                    # P2 task text and video
│   └── CA3/
│       ├── task.md             # converted assignment text
│       ├── crs.md              # coordinate reference systems
│       └── Proj-P3.mp4         # P3 video - placeholder
│
├── notebooks/
│   ├── CA1/Proj-P1.ipynb
│   ├── CA2/Proj-P2.ipynb
│   └── CA3/
│       ├── Proj-P3.ipynb       # executed CA3 notebook (hand-in)
│       ├── Proj-P3.py          # notebook source and analysis script
│       └── precompute_weather.py  # builds the shipped ERA5 caches
│
├── src/
│   ├── streamlit/
│   │   └── pages/              # home, table, diag, reservoir analysis,
│   │                           # weather quality, flows
│   └── utils/
│       ├── analysis.py         # STL, spectrogram, SPC and LOF helpers
│       ├── weather.py          # precomputed ERA5 series (both sources)
│       ├── cds_era5.py         # Copernicus CDS download and GRIB reader
│       ├── era5_cache.py       # build *_cds.parquet caches (parity mode)
│       ├── era5_openmeteo.py   # open-meteo's cell/elevation/rounding rules
│       ├── dataloader.py       # legacy P1 CSV loader, unused
│       ├── env.py              # secret loading (.secrets or st.secrets)
│       ├── magasin.py          # NVE Magasinstatistikk API + filling series
│       └── mongo.py            # MongoDB access for the flows page
│
├── tests/
│   ├── conftest.py             # repo path and the notebook-module fixture
│   ├── test_analysis.py        # helpers, data functions, property tests
│   └── test_weather_sources.py # parity, cache naming, source routing
│
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
├── uv.lock
├── streamlit_app.py            # Streamlit entry point
└── README.md
```

## CA3 data and caching

- **Magasinstatistikk:** downloaded from the public NVE API and cached as
  `data/cache/magasinstatistikk.parquet` (about 14.9k rows, 1995 onwards).
- **NVE Atlas layers:** the electricity (`Budomraade`) and precipitation
  (`NVE_Region`) layers are read from the committed shapefiles in
  `data/shapefiles/atlas_nve/`. The ArcGIS GeoJSON export of the same layers is
  the fallback and is cached under `data/cache/`.
- **ERA5:** hourly area means from either the open-meteo archive API
  (`models=era5`) or the Copernicus Climate Data Store. The app serves
  precomputed 2024 caches for all eight areas from **both** sources; the
  **Data source** control on the weather page switches between them. The CDS
  caches are built in *parity mode* (every point rounded before averaging), so
  the two series agree to ≤0.017 K and precipitation is identical. Caches
  include the region, interval and number of sampled locations in the filename,
  so a small test download is never reused as the full-resolution result.
- **CDS key:** the two shipped series need no key. The weather page's
  *Advanced: bring your own CDS key* panel fetches one month for the selected
  area with the visitor's own key — the CDS licence is personal, so the
  author's key is never shipped or shared.
- **Open-meteo quota:** 600 requests/min, 5 000/hour, 10 000/day, weighted by
  variables and days; one location still costs a full request inside a
  multi-location call. A 1000-location area-year is about 5 200 weighted calls
  and crosses the hourly limit — download one area at a time and pace the
  batches.

## Coordinate reference systems

Three CRSs, each at a fixed boundary: **EPSG:25833** (NVE's source data),
**EPSG:4326** (GeoJSON, open-meteo, figures) and **EPSG:3035** (equal-area
sampling in the ERA5 precompute). The Streamlit app carries no geometry at all.
Read [`docs/CA3/crs.md`](docs/CA3/crs.md) before touching coordinates — it records where
each one is used, why, and the measured sampling bias that comes from getting it wrong.

## Running locally

```bash
# Install the locked dependencies
uv sync

# Run the CA3 analysis as a script (STL + spectrogram + NO3 2024 weather)
.venv/bin/python notebooks/CA3/Proj-P3.py

# Run the test suite (pytest is in the dev dependency group)
env -u PYTHONPATH .venv/bin/python -m pytest

# Rebuild the shipped ERA5 caches (needs a CDS key in .secrets)
.venv/bin/python notebooks/CA3/precompute_weather.py --source cds

# Start the Streamlit app
.venv/bin/streamlit run streamlit_app.py
```

The app reads MongoDB and ENTSO-E credentials through `src/utils/env.py`.
Locally they live in `.secrets/secrets.toml` (gitignored); on Streamlit
Community Cloud they must be entered in the app's secrets settings.
