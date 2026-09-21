from pathlib import Path
import pandas as pd
import streamlit as st

class ReservoirData:
    """
    'reservoirs.csv' Data class for loading and light pre-processing reservoir data.
    """
    
    def __init__(self, csv_filename: str = "reservoirs.csv"):
        self.csv_filename = csv_filename
        self.repo_root: Path = Path(__file__).parent.parent.parent # Fetch repo root directory
        self.csv_path: Path = self.repo_root / "data" / self.csv_filename # Construct path to reservoirs.csv

    @st.cache_data
    def load_csv_raw(_self) -> pd.DataFrame: # Using _self to avoid streamlit caching issues
        """
        Load the reservoir data from the CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data.
        
        Raises:
            FileNotFoundError: CSV file missing.
        """
        
        if not _self.csv_path.exists():
            raise FileNotFoundError(_self.csv_path)
        
        return pd.read_csv(_self.csv_path)
    
    @st.cache_data
    def load_csv(_self) -> pd.DataFrame: # Using _self to avoid streamlit caching issues
        """
        Load the reservoir data from the CSV file, convert column names to English and sets data types.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data with English column names.
        """
        df = _self.load_csv_raw()
        df = _self.csv_nob_to_eng(df)
        return _self.set_df_dtypes(df)

    def csv_nob_to_eng(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Norwegian column names to English.

        Args:
            df (pd.DataFrame): DataFrame with Norwegian column names.

        Returns:
            pd.DataFrame: DataFrame with English column names.
        """
        translation_dict = {
            "dato_Id": "date",
            "omrType": "area_type",
            "omrnr": "area_number",
            "iso_aar": "iso_year",
            "iso_uke": "iso_week",
            "fyllingsgrad": "water_level",
            "kapasitet_TWh": "twh_cap",
            "fylling_TWh": "twh_fill",
            "neste_Publiseringsdato": "next_publication_date",
            "fyllingsgrad_forrige_uke": "water_level_prev_week",
            "endring_fyllingsgrad": "water_level_change"
        }
        
        return df.rename(columns=translation_dict)
    
    def set_df_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set appropriate data types for the DataFrame columns.

        Args:
            df (pd.DataFrame): DataFrame to set data types for.
        
        Returns:
            pd.DataFrame: DataFrame with updated data types.
        """
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d') # Example: 1995-09-03
        df['area_type'] = df['area_type'].astype(str)
        df['area_number'] = df['area_number'].astype(int)
        df['iso_year'] = df['iso_year'].astype(int)
        df['iso_week'] = df['iso_week'].astype(int)
        df['water_level'] = df['water_level'].astype(float)
        df['twh_cap'] = df['twh_cap'].astype(float)
        df['twh_fill'] = df['twh_fill'].astype(float)
        df['next_publication_date'] = pd.to_datetime(df['next_publication_date'], format='%Y-%m-%dT%H:%M:%S') # Example: 2023-08-23T13:00:00
        df['water_level_prev_week'] = df['water_level_prev_week'].astype(float)
        df['water_level_change'] = df['water_level_change'].astype(float)
        
        return df
    
    def select_columns(self, df: pd.DataFrame, columns: list[str]) -> pd.Series | pd.DataFrame:
        """
        Select specific columns from the DataFrame.

        Args:
            df (pd.DataFrame): Original DataFrame.
            columns (list[str]): List of column names to select.
        
        Returns:
            pd.Series | pd.DataFrame: Series or DataFrame containing only the selected columns.
        """
        return df[columns]