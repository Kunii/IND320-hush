"""MongoDB access for the curated ENTSOE cross-border flow data.

The collection is written by ``notebooks/CA2/Proj-P2.ipynb`` and read by the
Cross-border flows Streamlit page.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from pymongo import MongoClient
from pymongo.collection import Collection

from src.utils.env import secrets

DB_NAME = "ind320"
COLLECTION_NAME = "entsoe_flows"
MWH_PER_TWH = 1000000

FLOW_COLUMNS = ("timestamp", "direction", "quantity")


def _empty_flows() -> pd.DataFrame:
    """Return an empty flow table with the expected columns."""
    return pd.DataFrame(columns=FLOW_COLUMNS)


def _mongo_url() -> str:
    """Build the MongoDB URL from the configured username and password."""
    username = secrets.get_required("mongo_db.username")
    password = secrets.get_required("mongo_db.password")
    return (
        secrets.get_required("mongo_db.url")
        .replace("<username>", username)
        .replace("<password>", password)
    )


@st.cache_resource(show_spinner=False)
def get_collection() -> Collection:
    """
    Create one MongoDB client per Streamlit session/process.

    The connection string uses placeholders so the same structure works locally
    (.secrets/secrets.toml) and in Streamlit Cloud (app secrets).
    """
    client = MongoClient(_mongo_url(), serverSelectionTimeoutMS=15000)
    client.admin.command("ping")
    return client[DB_NAME][COLLECTION_NAME]


@st.cache_data(ttl=600, show_spinner=False)
def get_borders() -> list[str]:
    """Return the connection codes available in the curated collection."""
    return sorted(get_collection().distinct("border"))


@st.cache_data(ttl=600, show_spinner=False)
def get_years(border: str) -> list[int]:
    """Return the years with data for one connection."""
    return sorted(get_collection().distinct("year", {"border": border}))


@st.cache_data(ttl=600, show_spinner=False)
def get_pie_totals(border: str, year: int) -> pd.DataFrame:
    """
    Aggregate export/import energy for one connection and year.

    Energy in TWh = sum(quantity MW * hours) / 1e6. The aggregation is done in
    MongoDB so the page does not transfer the full set of observations.
    """
    pipeline = [
        {"$match": {"border": border, "year": year}},
        {
            "$group": {
                "_id": "$direction",
                "twh": {
                    "$sum": {
                        "$divide": [
                            {"$multiply": ["$quantity", "$hours"]},
                            MWH_PER_TWH,
                        ]
                    }
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]

    rows = list(get_collection().aggregate(pipeline))
    return pd.DataFrame(
        [{"direction": row["_id"], "twh": row["twh"]} for row in rows],
        columns=["direction", "twh"],
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_flows(
    border: str,
    year: int,
    months: tuple[int, ...],
) -> pd.DataFrame:
    """
    Return timestamp, direction and quantity for the selected months.

    ``months`` is a tuple so Streamlit can hash it as a cache key. The pipeline
    filters in MongoDB and only sends the columns needed by the chart.
    """
    if not months:
        return _empty_flows()

    pipeline = [
        {"$match": {"border": border, "year": year}},
        {"$addFields": {"month": {"$month": "$timestamp"}}},
        {"$match": {"month": {"$in": list(months)}}},
        {
            "$project": {
                "_id": 0,
                "timestamp": 1,
                "direction": 1,
                "quantity": 1,
            }
        },
        {"$sort": {"timestamp": 1}},
    ]

    rows = list(get_collection().aggregate(pipeline))
    if not rows:
        return _empty_flows()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.loc[:, FLOW_COLUMNS]
