# pages/5_Content_Removal.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(page_title="Content Removal · Observatory", page_icon="📋", layout="wide")

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.title("📋 Content Removal & Takedowns")

# ─────────────────────────────────────────────
# SAFE SQL BUILDER
# ─────────────────────────────────────────────
def sql_in(values):
    return ", ".join([f"'{v}'" for v in values]) if values else "''"


with st.sidebar:
    sources = st.multiselect(
        "Source",
        ["google_requests", "google_detailed", "lumen"],
        default=["google_requests", "google_detailed", "lumen"]
    )

src_sql = sql_in(sources)


# ─────────────────────────────────────────────
# DATA LOAD (ONLY FACT TABLE = TRUTH SOURCE)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_fact(src_sql):
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


df = load_fact(src_sql)

if df.empty:
    st.warning("No data for selected filters.")
    st.stop()


# ─────────────────────────────────────────────
# KPI ROW (SAFE)
# ─────────────────────────────────────────────
summary = df.groupby("source").agg({
    "number_of_requests": "sum",
    "items_requested_removal": "sum",
    "platform": "nunique",
    "requestor_name": "nunique"
}).reset_index()

cols = st.columns(len(summary))

for i, row in summary.iterrows():
    with cols[i]:
        st.metric(
            row["source"],
            f"{int(row['number_of_requests']):,}",
            help="Total takedown requests"
        )


st.divider()


# ─────────────────────────────────────────────
# TREND (NO EXTRA GROUPBY IN PYTHON)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_trends(src_sql):
    return run_query(f"""
        SELECT year_month, source, total_requests
        FROM {table('fact_takedown_trends')}
        WHERE source IN ({src_sql})
    """)

trend = load_trends(src_sql)

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
    font_color="#E8E6DF"
)

st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# TOP REASONS
# ─────────────────────────────────────────────
reason = (
    df.groupby("reason")["number_of_requests"]
    .sum()
    .sort_values()
    .tail(15)
    .reset_index()
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
    df.groupby(["requestor_name", "requestor_type"])["number_of_requests"]
    .sum()
    .sort_values()
    .tail(15)
    .reset_index()
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
    df.groupby(["reason", "platform"])["number_of_requests"]
    .sum()
    .reset_index()
)

pivot = heat.pivot(index="reason", columns="platform", values="number_of_requests").fillna(0)

fig_h = go.Figure(go.Heatmap(
    z=np.log1p(pivot.values),
    x=pivot.columns,
    y=pivot.index,
    colorscale="Reds"
))

st.plotly_chart(fig_h, use_container_width=True)
