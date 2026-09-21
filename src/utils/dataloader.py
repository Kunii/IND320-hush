from pathlib import Path
import pandas as pd
import streamlit as st

@st.cache_data
def load_res_csv():
    repo_root: Path = Path(__file__).parent.parent.parent # Fetch repo root directory
    csv_path: Path = repo_root / "data" / "reservoirs.csv" # Construct path to reservoirs.csv
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")
    
    return pd.read_csv(csv_path)
    