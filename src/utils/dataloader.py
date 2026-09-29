from pathlib import Path
import pandas as pd
import streamlit as st

class ReservoirData:
    """
    'reservoirs.csv' Data class for loading and light pre-processing reservoir data.
    """
    
    def __init__(self, csv_filename: str = "reservoirs.csv"):
        self.csv_filename: str = csv_filename
        self.repo_root: Path = Path(__file__).parent.parent.parent # Fetch repo root directory
        self.csv_path: Path = self.repo_root / "data" / self.csv_filename # Construct path to reservoirs.csv

    def load_csv_raw(self) -> pd.DataFrame:
        """
        Load the reservoir data from the CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data.
        
        Raises:
            FileNotFoundError: CSV file missing.
        """
        
        if not self.csv_path.exists():
            raise FileNotFoundError(self.csv_path)
        
        return pd.read_csv(self.csv_path)

    @st.cache_data
    def load_csv_raw_cached(_self) -> pd.DataFrame: # Using _self for streamlit
        """
        Streamlit cached version of load_csv_raw().
        Load the reservoir data from the CSV file.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data.
        
        Raises:
            FileNotFoundError: CSV file missing.
        """
        return _self.load_csv_raw()

    def load_csv(self) -> pd.DataFrame:
        """
        Load the reservoir data from the CSV file.
        Converts column names to English + all lowercase, sets explicit column data types.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data with English column names & strict column data types.
        """

        df: pd.DataFrame = self.load_csv_raw()

        df_raw_shape: tuple[int, int] = df.shape

        df = self.csv_nob_to_eng(df) # Convert norwegian to eng
        df = self.set_df_dtypes(df) # Set strict column data types

        if df.shape != df_raw_shape: # Just in case: check if the data shape changed, should NEVER trigger
            raise ValueError(f"DataFrame shape changed after processing: {df_raw_shape} -> {df.shape}")

        return df
    
    @st.cache_data
    def load_csv_cached(_self) -> pd.DataFrame: # Using _self for streamlit
        """
        Streamlit cached version of load_csv().
        Load the reservoir data from the CSV file.
        Converts column names to English + all lowercase, sets explicit column data types.

        Returns:
            pd.DataFrame: DataFrame containing the reservoir data with English column names & strict column data types.
        """
        return _self.load_csv() # Call the non-cached version

    def csv_nob_to_eng(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Norwegian column names to English + all lowercase.

        Mapping from (nor) -> to (eng):
            dato_Id -> date
            omrType -> area_type
            omrnr -> area_number
            iso_aar -> iso_year
            iso_uke -> iso_week
            fyllingsgrad -> water_level
            kapasitet_TWh -> twh_cap
            fylling_TWh -> twh_fill
            neste_Publiseringsdato -> next_publication_date
            fyllingsgrad_forrige_uke -> water_level_prev_week
            endring_fyllingsgrad -> water_level_change

        Args:
            df (pd.DataFrame): DataFrame with Norwegian column names.

        Returns:
            pd.DataFrame: DataFrame with English column names.
        """

        col_mapping: dict[str, str] = {
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
        
        return df.rename(columns=col_mapping)
    
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
    
    def filter_by_months(self, df: pd.DataFrame, month_count: int) -> pd.DataFrame:
        """
        Filter the DataFrame by a number of months.

        Args:
            df (pd.DataFrame): Original DataFrame.
            month_count (int): Number of months to filter by.
        
        Returns:
            pd.DataFrame: Filtered DataFrame containing only rows within the specified month count.
        """
        min_date = df['date'].min().to_period('M').to_timestamp() # Get the first day of the month from the "minimum" date
        last_date = min_date + pd.DateOffset(months=month_count) # Create end date for filter mask

        return df.loc[(df['date'] >= min_date) & (df['date'] <= last_date)] # Logical mask filtered dataframe