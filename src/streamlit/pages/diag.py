import streamlit as st

# Page 4

# A plot of the imported data (see below), including header, axis titles and other relevant formatting.
# A drop-down menu (st.selectbox) choosing any single column in the CSV or all columns together.
# A selection slider (st.select_slider) to select a subset of the months. The default should be the first month.

# Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed.
# In part 2 of the project, we will remove this file and rely on MongoDB instead.

st.title("Diagrams")
st.write(
    "Diagrams.."
)
