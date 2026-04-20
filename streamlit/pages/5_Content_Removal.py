import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from utils.bq_client import run_query, table, PALETTE


st.set_page_config(
    page_title="Content Removal · Observatory",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Content Removal & Takedowns")


# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

sources = st.multiselect(
    "Source",
    ["google_requests", "google_detailed", "lumen"],
    default=["google_requests", "google_detailed", "lumen"]
)

src_sql = ", ".join([f"'{s}'" for s in sources])


# ─────────────────────────────────────────────
# DATA LOAD (FIXED TABLE REFERENCE)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_fact():
    return run_query(f"""
        SELECT
            source,
            platform,
            reason,
            requestor_name,
            requestor_type,
            number_of_requests,
            items_requested_removal
        FROM {table('fact_takedown_requests')}
        WHERE source IN ({src_sql})
    """)

df = load_fact()

if df.empty:
    st.warning("No data available.")
    st.stop()


# ─────────────────────────────────────────────
# KPI
# ─────────────────────────────────────────────

summary = df.groupby("source", as_index=False).agg({
    "number_of_requests": "sum",
    "items_requested_removal": "sum",
    "platform": "nunique",
    "requestor_name": "nunique"
})

cols = st.columns(len(summary))

for i, row in summary.iterrows():
    cols[i].metric(
        row["source"],
        f"{int(row['number_of_requests']):,}"
    )


st.divider()


# ─────────────────────────────────────────────
# TREND (SAFE DERIVATION)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_trends():
    return run_query(f"""
        SELECT
            year_month,
            source,
            total_requests
        FROM {table('fact_takedown_trends')}
        WHERE source IN ({src_sql})
    """)

trend = load_trends()

fig = px.line(
    trend,
    x="year_month",
    y="total_requests",
    color="source",
    markers=True,
    title="Monthly Takedown Volume"
)

st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# REASONS
# ─────────────────────────────────────────────

reason = (
    df.groupby("reason", as_index=False)["number_of_requests"]
    .sum()
    .sort_values("number_of_requests")
    .tail(15)
)

fig_r = px.bar(
    reason,
    x="number_of_requests",
    y="reason",
    orientation="h",
    title="Top Removal Reasons"
)

st.plotly_chart(fig_r, use_container_width=True)


# ─────────────────────────────────────────────
# REQUESTORS
# ─────────────────────────────────────────────

req = (
    df.groupby(["requestor_name", "requestor_type"], as_index=False)["number_of_requests"]
    .sum()
    .sort_values("number_of_requests")
    .tail(15)
)

fig_req = px.bar(
    req,
    x="number_of_requests",
    y="requestor_name",
    color="requestor_type",
    orientation="h",
    title="Top Requestors"
)

st.plotly_chart(fig_req, use_container_width=True)


# ─────────────────────────────────────────────
# HEATMAP
# ─────────────────────────────────────────────

heat = (
    df.groupby(["reason", "platform"], as_index=False)["number_of_requests"]
    .sum()
)

pivot = heat.pivot(index="reason", columns="platform", values="number_of_requests").fillna(0)

fig_h = go.Figure(go.Heatmap(
    z=np.log1p(pivot.values),
    x=pivot.columns,
    y=pivot.index,
    colorscale="Reds"
))

st.plotly_chart(fig_h, use_container_width=True)
