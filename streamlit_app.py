import streamlit as st

# Page navigation. Each page is a separate file under src/streamlit/pages/.
pages = [
    st.Page("src/streamlit/pages/home.py", title="Home", icon="🏠"),
    st.Page("src/streamlit/pages/table.py", title="Reservoir table", icon="📋"),
    st.Page("src/streamlit/pages/diag.py", title="Reservoir plot", icon="📈"),
    st.Page("src/streamlit/pages/flows.py", title="Cross-border flows", icon="🌍"),
]

sidebar = st.navigation(pages, position="sidebar")
sidebar.run()
