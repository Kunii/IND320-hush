import streamlit as st
import pandas as pd
from src.utils.dataloader import ReservoirData

# Page 2

# A table showing the imported data (see below).
# Use the row-wise LineChartColumn() to display the first month of the data series.
# There should be one row in the table for each column of the imported data.

# Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed.
# In part 2 of the project, we will remove this file and rely on MongoDB instead.


class ReservoirTable:
    def __init__(self):
        self.rd = ReservoirData() # Create an instance of ReservoirData
        self.res_df = self.rd.load_csv_cached().sort_values(by='date') # Loads a lightly processed DF
        self.filtered_df = self.filter_first_month_data()

    def filter_first_month_data(self):
        
        data: pd.DataFrame = self.res_df.copy() # As to not modify the original DF
        first_month = self.rd.filter_by_months(data, 1) # Get the first month of the first year
        first_month.drop(columns=["area_type", "area_number", "iso_year", "iso_week", "next_publication_date"], inplace=True) # Drop columns that are not relevant for plotting

        value_columns = first_month.select_dtypes(include="number").columns # Omit columns with non-numeric data

        filtered_df = pd.DataFrame( # Reconstruct a strange dataframe for the line chart column plotting
            {
                "Column Name": value_columns, # Column of column names
                "First Month Values": [first_month[column].tolist() for column in value_columns] # Column of a list of values, where each row = column values
            }
        )
        
        return filtered_df
            
    def display_table(self):
        st.write("Reservoir table")
        st.dataframe(self.res_df) # Table view

    def display_first_month_table(self):
        st.write("First month table")
        st.dataframe(self.filtered_df) # Table view

    def display_line_chart(self):
        st.write("First month line charts")

        st.dataframe(self.filtered_df,
                        column_config={
                            "Column Name": st.column_config.TextColumn(label="Column Name"),
                            "First Month Values": st.column_config.LineChartColumn(
                                label="Plot",
                                help="Line chart of the first month values"
                            )
                        }
                     )
        
    def render(self):
        
        st.title("Reservoir Data CSV")
        st.write("Task 2")
        
        self.display_table()
        self.display_first_month_table()
        self.display_line_chart()

ReservoirTable().render()