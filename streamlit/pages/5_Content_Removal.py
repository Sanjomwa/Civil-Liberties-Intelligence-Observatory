# pages/5_Content_Removal.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from utils.bq_client import run_query, table, PALETTE
from utils.contracts import FACT_TAKEDOWN_REQUESTS_SCHEMA


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

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

if not sources:
    st.warning("Select at least one source")
    st.stop()

src_sql = ", ".join([f"'{s}'" for s in sources])


# ─────────────────────────────────────────────
# DATA LOAD (MART-BASED + SAFE)
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
        FROM {table("fact_takedown_requests")}
        WHERE source IN ({src_sql})
    """)


df = load_fact()

if df is None or df.empty:
    st.warning("No data available for selected filters.")
    st.stop()


# ─────────────────────────────────────────────
# CLEANING (SAFE NULL HANDLING)
# ─────────────────────────────────────────────

df["number_of_requests"] = df["number_of_requests"].fillna(0)
df["items_requested_removal"] = df["items_requested_removal"].fillna(0)


# ─────────────────────────────────────────────
# KPI BLOCK (SAFE AGGREGATION)
# ─────────────────────────────────────────────

summary = (
    df.groupby("source", as_index=False)
    .agg(
        number_of_requests=("number_of_requests", "sum"),
        items_requested_removal=("items_requested_removal", "sum"),
        platform=("platform", "nunique"),
        requestor_name=("requestor_name", "nunique"),
    )
)

cols = st.columns(len(summary))

for i, row in summary.iterrows():
    with cols[i]:
        st.metric(
            label=row["source"],
            value=f"{int(row['number_of_requests']):,}",
            help="Total takedown requests"
        )


st.divider()


# ─────────────────────────────────────────────
# TREND (MART SAFE)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_trends():
    return run_query(f"""
        SELECT
            year_month,
            source,
            total_requests
        FROM {table("fact_takedown_trends")}
        WHERE source IN ({src_sql})
        ORDER BY year_month
    """)


trend = load_trends()

if trend is None or trend.empty:
    st.warning("No trend data available.")
else:
    fig = px.line(
        trend,
        x="year_month",
        y="total_requests",
        color="source",
        markers=True,
        title="Monthly Takedown Volume"
    )

    fig.update_layout(
        plot_bgcolor="#0D0D0F",
        paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF",
    )

    st.plotly_chart(fig, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────
# REASONS (CLEAN TOP-K LOGIC)
# ─────────────────────────────────────────────

reason = (
    df.groupby("reason", as_index=False)["number_of_requests"]
    .sum()
    .sort_values("number_of_requests", ascending=True)
    .tail(15)
)

fig_r = px.bar(
    reason,
    x="number_of_requests",
    y="reason",
    orientation="h",
    title="Top Removal Reasons"
)

fig_r.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
)

st.plotly_chart(fig_r, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────
# REQUESTORS (STABLE GROUPING)
# ─────────────────────────────────────────────

req = (
    df.groupby(["requestor_name", "requestor_type"], as_index=False)["number_of_requests"]
    .sum()
    .sort_values("number_of_requests", ascending=True)
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

fig_req.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
)

st.plotly_chart(fig_req, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────
# HEATMAP (FIXED NULL + LOG SAFETY)
# ─────────────────────────────────────────────

heat = (
    df.groupby(["reason", "platform"], as_index=False)["number_of_requests"]
    .sum()
)

pivot = heat.pivot(
    index="reason",
    columns="platform",
    values="number_of_requests"
).fillna(0)

# prevent log(0) issues
heat_values = np.log1p(pivot.values)

fig_h = go.Figure(go.Heatmap(
    z=heat_values,
    x=pivot.columns.astype(str),
    y=pivot.index.astype(str),
    colorscale="Reds"
))

fig_h.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
)

st.plotly_chart(fig_h, use_container_width=True)
