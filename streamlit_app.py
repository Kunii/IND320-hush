import streamlit as st

# CRS: this app carries no geometry. Every series is keyed by area, not by
# coordinate — the projection and sampling happen once, offline, in
# notebooks/CA3 (EPSG:25833 source -> EPSG:3035 for the equal-area point pool
# -> EPSG:4326 for the weather API). See docs/crs.md before adding a map.

# Page navigation. Each page is a separate file under src/streamlit/pages/.
# Order groups the reservoir pages, then the two CA3 analysis pages, then flows.
pages = [
    st.Page("src/streamlit/pages/home.py", title="Home", icon="🏠"),
    st.Page("src/streamlit/pages/table.py", title="Reservoir table", icon="📋"),
    st.Page("src/streamlit/pages/diag.py", title="Reservoir plot", icon="📈"),
    st.Page(
        "src/streamlit/pages/reservoir_analysis.py",
        title="Reservoir analysis",
        icon="📉",
    ),
    st.Page(
        "src/streamlit/pages/weather_quality.py",
        title="Weather quality",
        icon="🌦️",
    ),
    st.Page("src/streamlit/pages/flows.py", title="Cross-border flows", icon="🌍"),
]

sidebar = st.navigation(pages, position="sidebar")
sidebar.run()
