import streamlit as st
from src.utils.env import secrets

# Top-level keys
db_user = secrets.get_required("DB_USERNAME")
db_token = secrets.get("DB_TOKEN")


st.title("IND320 - Robin E")
st.write(
    "Hello :)"
)
