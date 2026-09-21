import streamlit as st
import pandas as pd
from src.utils.dataloader import load_res_csv

# Page 3

# A table showing the imported data (see below).
# Use the row-wise LineChartColumn() to display the first month of the data series.
# There should be one row in the table for each column of the imported data.

# Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed.
# In part 2 of the project, we will remove this file and rely on MongoDB instead.

class ReservoirTable:
    def __init__(self):
        self.res_df = load_res_csv()
        self.filtered_df = self.filter_first_month_data()

    def filter_first_month_data(self):
        data = self.res_df.copy() # Dont modify the original dataframe
        data = data[["dato_Id", "fyllingsgrad", "fyllingsgrad_forrige_uke", "endring_fyllingsgrad", "kapasitet_TWh", "fylling_TWh"]] # Select relevant columns
        
        data["dato_Id"] = pd.to_datetime(data["dato_Id"]) # Convert the "dato_Id" column to datetime object
        
        first_year = data[data["dato_Id"].dt.year == data["dato_Id"].dt.year.min()] # Get the first year in the dataset
        first_month = first_year[first_year["dato_Id"].dt.month ==first_year["dato_Id"].dt.month.min()] # Get the first month in the first year
        
        value_columns = first_month.select_dtypes(include="number").columns # Omit columns with non-numeric data
        
        filtered_df = pd.DataFrame(
            {
                "col": value_columns,
                "first_month": [
                    first_month[column].tolist() for column in value_columns
                ],
            }
        )
        
        return filtered_df
    
    def display_table(self):
        st.write("Reservoir Data Table")
        st.dataframe(self.res_df)

    def display_first_month_table(self):
        st.write("Reservoir First Month Data Table")
        st.dataframe(self.filtered_df)

    def display_line_chart(self):
        st.write("Reservoir first month data line chart")

        st.dataframe(self.filtered_df,
                        column_config={
                            "col": st.column_config.TextColumn("Column Name"),
                            "first_month": st.column_config.LineChartColumn(
                                "First Month Data",
                                width="medium",
                                help="Line chart of the first month data",
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