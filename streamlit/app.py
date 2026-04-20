# app.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(
    page_title="Internet Freedom Observatory",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Internet Freedom Observatory")
st.caption("Real-time monitoring of internet censorship, conflict, and platform suppression.")

# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data():
    return run_query(f"""
        SELECT *
        FROM {table('civil_liberties_mart')}
    """)

df = load_data()

# ─────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────

total_measurements = df["total_measurements"].sum()
blocked_total = df["blocked_count"].sum()
avg_block_rate = df["blocking_rate"].mean() * 100

protest_blocks = df[df["blocked_on_protest_day"]]["blocked_count"].sum()
total_blocks = blocked_total if blocked_total > 0 else 1
protest_block_pct = (protest_blocks / total_blocks) * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Measurements", f"{total_measurements:,.0f}")
c2.metric("Blocked Tests", f"{blocked_total:,.0f}")
c3.metric("Avg Blocking Rate", f"{avg_block_rate:.1f}%")
c4.metric("Protest-linked Blocking", f"{protest_block_pct:.1f}%")

st.divider()

# ─────────────────────────────────────────────────────────────
# MONTHLY TIMELINE
# ─────────────────────────────────────────────────────────────

timeline = (
    df.groupby("year_month")
    .agg({
        "blocked_count": "sum",
        "total_measurements": "sum"
    })
    .reset_index()
)

timeline["blocking_rate"] = timeline["blocked_count"] / timeline["total_measurements"]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=timeline["year_month"],
    y=timeline["blocked_count"],
    name="Blocked",
    marker_color=PALETTE["coral"],
    opacity=0.7
))
fig.add_trace(go.Scatter(
    x=timeline["year_month"],
    y=timeline["blocking_rate"] * 100,
    name="Blocking %",
    line=dict(color=PALETTE["amber"], width=2),
    mode="lines+markers",
    yaxis="y2"
))

fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=400,
    yaxis=dict(title="Blocked Count"),
    yaxis2=dict(title="Blocking %", overlaying="y", side="right"),
    xaxis=dict(tickangle=45),
    legend=dict(orientation="h", y=1.05)
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────
# SUPPRESSION WINDOWS
# ─────────────────────────────────────────────────────────────

st.markdown("### 🧠 Suppression Windows")

windows = (
    df.groupby("suppression_window_type")
    .agg({
        "blocked_count": "sum"
    })
    .reset_index()
    .sort_values("blocked_count", ascending=False)
)

fig_win = px.bar(
    windows,
    x="blocked_count",
    y="suppression_window_type",
    orientation="h",
    color="suppression_window_type",
    height=350
)

fig_win.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False
)

st.plotly_chart(fig_win, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# PLATFORM OVERVIEW
# ─────────────────────────────────────────────────────────────

st.markdown("### 🔒 Top Blocked Platforms")

platforms = (
    df.groupby("platform")
    .agg({
        "blocked_count": "sum",
        "total_measurements": "sum"
    })
    .reset_index()
)

platforms["blocking_rate"] = platforms["blocked_count"] / platforms["total_measurements"]

top_platforms = platforms.sort_values("blocking_rate", ascending=False).head(15)

fig_plat = px.bar(
    top_platforms.sort_values("blocking_rate"),
    x="blocking_rate",
    y="platform",
    orientation="h",
    text=top_platforms["blocking_rate"].round(2),
    height=400
)

fig_plat.update_traces(texttemplate="%{text:.0%}", textposition="outside")

fig_plat.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    xaxis=dict(title="Blocking Rate"),
    yaxis=dict(title="")
)

st.plotly_chart(fig_plat, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# DATA TABLE
# ─────────────────────────────────────────────────────────────

st.markdown("### 📊 Raw Data")

st.dataframe(
    df[[
        "measurement_date",
        "country",
        "platform",
        "blocking_rate",
        "blocked_count",
        "conflict_events",
        "total_takedown_requests",
        "suppression_window_type"
    ]],
    use_container_width=True,
    hide_index=True
)
