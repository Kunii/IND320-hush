# IND320 Project - RTE

## Streamlit app

[Main](https://ind320-hush.streamlit.app)  

## Project parts

| Part | Topic | Notebook / script | Task text |
|---|---|---|---|
| CA1 | Data sources and first Streamlit app | `notebooks/CA1/Proj-P1.ipynb` | `docs/CA1/task.md` |
| CA2 | Cassandra, MongoDB and ENTSO-E flows | `notebooks/CA2/Proj-P2.ipynb` | `docs/CA2/task.md` |
| CA3 | Data quality: STL, spectrogram, SPC and LOF | `notebooks/CA3/Proj-P3.ipynb` (+ `Proj-P3.py` script) | `docs/CA3/task.md` |

## Repository structure

```txt
├── data/
│   ├── Y_eicCodes.csv          # ENTSO-E area codes
│   ├── cache/                  # generated parquet/GeoJSON caches (gitignored)
│   └── shapefiles/             # optional official NVE shapefiles (gitignored)
│
├── docs/
│   ├── CA1/                    # P1 task text and video
│   ├── CA2/                    # P2 task text and video
│   └── CA3/                    # P3 task text and video

│
├── notebooks/
│   ├── CA1/Proj-P1.ipynb
│   ├── CA2/Proj-P2.ipynb
│   └── CA3/
│       ├── Proj-P3.ipynb       # executed CA3 notebook (hand-in)
│       ├── Proj-P3.html        # self-contained HTML export
│       ├── Proj-P3.pdf         # PDF export
│       ├── Proj-P3.py          # working CA3 analysis script
│       └── test_proj_p3.py     # self-tests for the analysis helpers
│
├── src/
│   ├── streamlit/
│   │   └── pages/              # app pages (home, table, diag, flows)
│   └── utils/
│       ├── dataloader.py       # legacy P1 CSV loader, unused
│       ├── env.py              # secret loading (.secrets or st.secrets)
│       ├── magasin.py          # NVE Magasinstatistikk API
│       └── mongo.py            # MongoDB access for the flows page
│
├── .devcontainer/
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
- **ERA5:** downloaded from `archive-api.open-meteo.com` and reduced to daily
  area means while downloading. Caches include the region, interval and number
  of sampled locations in the filename, so a small test download is never
  reused as the full-resolution result.
- **Open-meteo quota:** the free tier is 10,000 weighted calls per day.
  A 1000-location area-year is several thousand calls; download one area at a
  time and check the quota before a full multi-area run.

## Coordinate reference systems

Three CRSs, each at a fixed boundary: **EPSG:25833** (NVE's source data),
**EPSG:4326** (GeoJSON, open-meteo, figures) and **EPSG:3035** (equal-area
sampling in the ERA5 precompute). The Streamlit app carries no geometry at all.
Read [`docs/crs.md`](docs/crs.md) before touching coordinates — it records where
each one is used, why, and the measured sampling bias that comes from getting it
wrong.

## Running locally

```bash
# Install the locked dependencies
uv sync

# Run the CA3 analysis as a script (STL + spectrogram + NO3 2024 weather)
.venv/bin/python notebooks/CA3/Proj-P3.py

# Run the analysis self-tests
.venv/bin/python notebooks/CA3/test_proj_p3.py

# Start the Streamlit app
.venv/bin/streamlit run streamlit_app.py
```

The app reads MongoDB and ENTSO-E credentials through `src/utils/env.py`.
Locally they live in `.secrets/secrets.toml` (gitignored); on Streamlit
Community Cloud they must be entered in the app's secrets settings.
