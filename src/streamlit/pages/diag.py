import streamlit as st
import pandas as pd
from src.utils.dataloader import ReservoirData

# Page 3

# A plot of the imported data (see below), including header, axis titles and other relevant formatting.
# A drop-down menu (st.selectbox) choosing any single column in the CSV or all columns together.
# A selection slider (st.select_slider) to select a subset of the months. The default should be the first month.

# Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed.
# In part 2 of the project, we will remove this file and rely on MongoDB instead.

class DiagPage:
    def __init__(self):
        self.rd = ReservoirData()  # Create an instance of ReservoirData
        self.res_df: pd.DataFrame = self.rd.load_csv_cached().sort_values(by='date') # Loads a lightly processed DF
        self.valid_plot_columns: list[str] = ['twh_cap', 'twh_fill', 'water_level', 'water_level_prev_week', 'water_level_change'] # List of valid columns for plotting
        self.filtered_df = self.filter_df(1, 0, 'all')
      
    def filter_df(self, months: int, area_number, col: str) -> pd.DataFrame:
        
        data: pd.DataFrame = self.res_df.copy() # As to not modify the original DF
        cols = ["date", col]
              
        month_df = self.rd.filter_by_months(data, months) # Get the first month of the first year
        month_df = month_df[month_df["area_number"] == area_number]
        month_df.drop(columns=["area_type", "area_number", "iso_year", "iso_week", "next_publication_date"], inplace=True)  # Drop columns that are not relevant for plotting
        
        if col != "all":
            month_df = month_df[cols] # Keep only the selected columns and the date column
        
        # Normalize columns
        for col in self.valid_plot_columns:
            if col in month_df.columns:
                min_val = month_df[col].min()
                max_val = month_df[col].max()
                val_range = max_val - min_val
                normalized = (month_df[col] - min_val) / (val_range) if val_range != 0 else 1.0  # Normalize to 1.0 if range is zero, otherwise use range normalized value
                month_df[col] = normalized
        
        return month_df

    def display_df(self):
        st.write("Reservoir plot")
        
        self.filtered_df = self.filter_df(st.session_state.months, st.session_state.area_number, st.session_state.columns)
        st.line_chart(self.filtered_df.set_index("date"), y_label="Normalized Values", x_label="Date")
       
    def render(self):
        
        st.title("Reservoir Data Plot")
        st.write("Task 3")
        
        st.session_state.columns = st.selectbox("Select Column", options=["all"] + self.valid_plot_columns)
        st.session_state.area_number = st.selectbox("Select Area Number", options=self.res_df["area_number"].unique())
        st.session_state.months = st.slider("Select Number of Months", min_value=1, max_value=self.res_df["date"].dt.year.nunique() * 12, value=1, step=1)
        
        self.display_df()


DiagPage().render()