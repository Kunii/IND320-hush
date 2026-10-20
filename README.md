# IND320 Project - RTE

[Streamlit page](https://ind320-hush.streamlit.app)

## Repo structure

```txt
├── .devcotainer/                # Streamlit autogen stuff
├── .github/                     # Streamlit autogen stuff
|
├── data/                        # Data files
|     └── Y_eicCodes.csv         # EIC codes CSV
|
├── docs/                        # Project document files
|     ├── CA1/                   # Project part 1 files
|     |     └── task.md          # Task description
|     |
|     └── CA2/                   # Project part 2 files
|           ├── task.md          # Task description
|           └── Proj-P2.mp4      # Video file
|
├── notebooks/                   # Project notebooks
|     ├── CA1/
|     |     └── Proj-P1.ipynb     # Project Part 1 notebook
|     └── CA2/
|           └── Proj-P2.ipynb     # Project Part 2 notebook
|
├── src/                         # Package root
|     ├── streamlit/             # Streamlit specific code
|     |     ├── components/      # Page components - Planned, currently unused
|     |     └── pages/           # Pages
|     |          ├── diag.py     # Diagram page
|     |          ├── flows.py    # Flows page
|     |          ├── home.py     # Home page
|     |          └── table.py    # Table view page
|     |
|     └──utils/                  # General utility code
|           ├── dataloader.py    # OLD - To be removed / rewritten - Dataloader stuff, eg. ReservoirData for 'data/reservoirs.csv'
|           ├── magasin.py       # NVE Api stuff
|           ├── mongo.py         # MongoDB stuff
|           └── env.py           # Secrets file stuff
|
├── .gitignore                   # Git ignored content
├── .python-version              # Streamlit autogen
├── LICENSE                      # Streamlit autogen
├── pyproject.toml               # Python project file - Based on autogen streamlit
├── uv.lock                      # Package dependencies - Based on autogen streamlit
└── streamlit_app.py             # Streamlit run entry point
```
