# pages/4_Regional_Conflict_Map.py

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.bq_client import run_query, table, PALETTE


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Kenya Geo Pressure Map",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Kenya Geo Pressure Map")
st.caption(
    "Spatial distribution of conflict + censorship intensity (country-level proxy view)")


# ─────────────────────────────────────────────
# GLOBAL FILTERS (HARD FIXED RANGE)
# ─────────────────────────────────────────────

DEFAULT_START = "2023-06-01"
DEFAULT_END = "2025-06-30"

start_date = st.session_state.get("start_date", DEFAULT_START)
end_date = st.session_state.get("end_date", DEFAULT_END)


# ─────────────────────────────────────────────
# DATA LOAD (GEO ENABLED MART)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            country_name,
            latitude,
            longitude,

            conflict_events,
            fatalities,
            block_rate,
            civil_liberties_pressure_index,
            suppression_window

        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
    """)


df = load_data(start_date, end_date)

if df.empty:
    st.warning("No data available for selected range.")
    st.stop()


# ─────────────────────────────────────────────
# AGGREGATE TO GEO LEVEL (IMPORTANT FIX)
# ─────────────────────────────────────────────

geo_df = (
    df.groupby(
        ["country_name", "latitude", "longitude"],
        as_index=False
    )
    .agg({
        "conflict_events": "sum",
        "fatalities": "sum",
        "block_rate": "mean",
        "civil_liberties_pressure_index": "mean"
    })
)


# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Conflict Events", f"{geo_df['conflict_events'].sum():,.0f}")
c2.metric("Total Fatalities", f"{geo_df['fatalities'].sum():,.0f}")
c3.metric("Avg Block Rate", f"{geo_df['block_rate'].mean()*100:.2f}%")
c4.metric("Avg Pressure Index",
          f"{geo_df['civil_liberties_pressure_index'].mean():.2f}")

st.divider()


# ─────────────────────────────────────────────
# GEO MAP (CORE FIX)
# ─────────────────────────────────────────────

fig = px.scatter_geo(
    geo_df,

    lat="latitude",
    lon="longitude",

    size="conflict_events",
    color="civil_liberties_pressure_index",

    hover_name="country_name",

    hover_data={
        "conflict_events": True,
        "fatalities": True,
        "block_rate": ":.2%",
        "civil_liberties_pressure_index": ":.2f",
        "latitude": False,
        "longitude": False,
    },

    projection="natural earth",
    color_continuous_scale="Turbo"
)

fig.update_layout(
    title="Geo Distribution of Conflict vs Censorship Pressure",
    paper_bgcolor="#0D0D0F",
    plot_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    margin=dict(l=0, r=0, t=40, b=0)
)

st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# SUPPRESSION WINDOW BREAKDOWN
# ─────────────────────────────────────────────

st.subheader("🧠 Suppression Window Distribution")

window_df = (
    df.groupby("suppression_window", as_index=False)
    .size()
    .rename(columns={"size": "count"})
)

fig2 = px.bar(
    window_df,
    x="count",
    y="suppression_window",
    orientation="h",
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False,
)

st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
# TIME FILTERED INTENSITY VIEW
# ─────────────────────────────────────────────

st.subheader("📈 Time Trend (National Aggregation)")

time_df = (
    df.groupby("measurement_date", as_index=False)
    .agg({
        "conflict_events": "sum",
        "civil_liberties_pressure_index": "mean"
    })
)

st.line_chart(
    time_df.set_index("measurement_date")[[
        "conflict_events",
        "civil_liberties_pressure_index"
    ]]
)
