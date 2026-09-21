import streamlit as st
import pandas as pd
from src.utils.dataloader import ReservoirData

# Page 3

# A table showing the imported data (see below).
# Use the row-wise LineChartColumn() to display the first month of the data series.
# There should be one row in the table for each column of the imported data.

# Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed.
# In part 2 of the project, we will remove this file and rely on MongoDB instead.

class ReservoirTable:
    def __init__(self):
        self.rd = ReservoirData()  # Create an instance of ReservoirData
        self.res_df = self.rd.load_csv() # Loads a lightly processed DF
        self.filtered_df = self.filter_first_month_data()

    def filter_first_month_data(self):
        data = self.res_df.copy()[["date", "water_level", "water_level_prev_week", "water_level_change", "twh_cap", "twh_fill"]] # As to not modify the original DF
        first_year = data[data["date"].dt.year == data["date"].dt.year.min()] # Get the first year in the dataset
        first_month = first_year[first_year["date"].dt.month == first_year["date"].dt.month.min()] # Get the first month of the first year

        #print(f"Unique years (should be 1995): {first_year["date"].dt.year.unique()}") # Sanity check - Get the unique years in the first year dataframe
        #print(f"Unique months (should be 1): {first_month["date"].dt.month.unique()}") # Sanity check - Get the unique months in the first month dataframe
                
        value_columns = first_month.select_dtypes(include="number").columns # Omit columns with non-numeric data

        filtered_df = pd.DataFrame(
            {
                "Column Name": value_columns, # Column of original column names
                "First Month Values": [ # Values as a list
                    first_month[column].tolist() for column in value_columns
                ],
            }
        )
        
        return filtered_df
            
    def display_table(self):
        st.write("Reservoir Data Table")
        st.dataframe(self.res_df)

    def display_first_month_table(self):
        st.write("Reservoir first month data table")
        st.dataframe(self.filtered_df)

    def display_line_chart(self):
        st.write("Reservoir first month data line charts")

        st.dataframe(self.filtered_df,
                        column_config={
                            "Column Name": st.column_config.TextColumn(label="Column Name"),
                            "First Month Values": st.column_config.LineChartColumn(
                                label="First Month Plot",
                                help="Line chart of the first month values",
                                y_min=0,
                                y_max=100
                            )
                        }
                     )
        
    def render(self):
        
        st.title("Reservoir Data CSV")
        
        self.display_table()
        self.display_first_month_table()
        self.display_line_chart()

ReservoirTable().render()