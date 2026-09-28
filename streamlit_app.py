import streamlit as st

# Page 1
# The front/home page should have a sidebar menu with navigation options to the other pages.

pages = []

page_home = st.Page("src/streamlit/pages/home.py", title="Home", icon="🏠")
page_diag = st.Page("src/streamlit/pages/diag.py", title="Diagram", icon="📊")
page_table = st.Page("src/streamlit/pages/table.py", title="Table view", icon="📋")
page_dummy = st.Page("src/streamlit/pages/dummy.py", title="Dummy", icon="📄")

pages.append(page_home)
pages.append(page_table)
pages.append(page_diag)
pages.append(page_dummy)

sidebar = st.navigation(pages, position="sidebar")

sidebar.run()