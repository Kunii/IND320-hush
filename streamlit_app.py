import streamlit as st
#from src.utils.env import secrets

# Top-level keys
#db_user = secrets.get_required("DB_USERNAME")
#db_token = secrets.get("DB_TOKEN")

# Page 1
# The front/home page should have a sidebar menu with navigation options to the other pages.

with st.sidebar:
    st.write("Sidebar content")

pages = []

page_home = st.Page("src/streamlit/pages/home.py", title="Home", icon="🏠")
page_diag = st.Page("src/streamlit/pages/diag.py", title="Diagrams", icon="📊")
page_table = st.Page("src/streamlit/pages/table.py", title="Table view", icon="📋")

pages.append(page_home)
pages.append(page_diag)
pages.append(page_table)

sidebar = st.navigation(pages, position="sidebar")
sidebar.run()