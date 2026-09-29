# IND320 Project - RTE

## Repo structure

```txt
├── .devcotainer/                # Streamlit autogen stuff
├── .github/                     # Streamlit autogen stuff
|
├── data/                        # Data files
|     └── reservoirs.csv         # Project part 1 data csv
|
├── docs/                        # Project document files
|     └── CA1/                   # Project part 1 files
|           └── task.md          # Task description
|
├── notebooks/                   # Project notebooks
|     └── Proj-P1.ipynb          # Project Part 1 notebook
|
├── src/                         # Package root
|     ├── streamlit/             # Streamlit specific code
|     |     ├── components/      # Page components - Planned, currently unused
|     |     └── pages/           # Pages
|     |          ├── diag.py     # Diagram page
|     |          ├── dummy.py    # Dummy page
|     |          ├── home.py     # Home page
|     |          └── table.py    # Table view page
|     |
|     └──utils/                  # General utility code
|           ├── dataloader.py    # Dataloader stuff, eg. ReservoirData for 'data/reservoirs.csv'
|           └── env.py           # Secrets file stuff
|
├── .gitignore                   # Git ignored content
├── .python-version              # Streamlit autogen
├── LICENSE                      # Streamlit autogen
├── pyproject.toml               # Python project file - Based on autogen streamlit
├── uv.lock                      # Package dependencies - Based on autogen streamlit
└── streamlit_app.py             # Streamlit run entry point
```
