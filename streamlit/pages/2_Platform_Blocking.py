# pages/2_Platform_Blocking.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE

st.set_page_config(
    page_title="Platform Blocking",
    page_icon="🔒",
    layout="wide",
)

st.title("🔒 Platform Blocking Intelligence")
st.caption("Which platforms are under sustained censorship pressure across Kenya (2023–2025)")


# ─────────────────────────────────────────────────────────────
# GLOBAL FILTERS
# ─────────────────────────────────────────────────────────────

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")
selected_platforms = st.session_state.get("platforms", [])


platform_filter_sql = ""
if selected_platforms:
    platform_filter_sql = f"AND platform IN UNNEST(@platforms)"


# ─────────────────────────────────────────────────────────────
# DATA LOAD (ONLY PLATFORM MART)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_platform_data(start_date, end_date, platforms):
    sql = f"""
        SELECT
            measurement_date,
            platform,
            block_rate,
            blocked,
            tests,
            takedown_requests,
            items_removed,
            platform_pressure_score
        FROM {table("platform_censorship_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        {platform_filter_sql}
        ORDER BY measurement_date
    """

    return run_query(sql)


df = load_platform_data(start_date, end_date, selected_platforms)


# ─────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────

c1, c2, c3 = st.columns(3)

c1.metric("Avg Block Rate", f"{df['block_rate'].mean() * 100:.2f}%")
c2.metric("Total Blocked Tests", f"{df['blocked'].sum():,.0f}")
c3.metric("Avg Pressure Score", f"{df['platform_pressure_score'].mean():.2f}")

st.divider()


# ─────────────────────────────────────────────────────────────
# TOP PLATFORMS (PRESSURE RANKING)
# ─────────────────────────────────────────────────────────────

top = (
    df.groupby("platform", as_index=False)
    .agg({
        "block_rate": "mean",
        "platform_pressure_score": "mean",
        "blocked": "sum"
    })
    .sort_values("block_rate", ascending=False)
    .head(15)
)

fig = px.bar(
    top.sort_values("block_rate"),
    x="block_rate",
    y="platform",
    orientation="h",
    text=(top["block_rate"] * 100).round(1),
)

fig.update_traces(texttemplate="%{text}%", textposition="outside")

fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    xaxis=dict(title="Block Rate"),
    yaxis=dict(title=""),
)

st.plotly_chart(fig, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────────────────────
# PLATFORM × TIME HEATMAP
# ─────────────────────────────────────────────────────────────

st.subheader("📊 Platform Blocking Over Time")

top_platforms = (
    df.groupby("platform")["block_rate"]
    .mean()
    .sort_values(ascending=False)
    .head(20)
    .index.tolist()
)

heat_df = df[df["platform"].isin(top_platforms)].copy()

heat_df["year_month"] = pd.to_datetime(
    heat_df["measurement_date"]
).dt.to_period("M").astype(str)

pivot = heat_df.pivot_table(
    index="platform",
    columns="year_month",
    values="block_rate",
    aggfunc="mean"
).fillna(0)

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns,
    y=pivot.index,
    colorscale=[
        [0.0, "#16161A"],
        [0.3, "#042C53"],
        [0.6, "#185FA5"],
        [1.0, "#E8593C"],
    ],
    text=[[f"{v*100:.0f}%" if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    textfont=dict(size=9),
    showscale=True,
))

fig_heat.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=500,
    margin=dict(l=120, r=20, t=20, b=60),
)

st.plotly_chart(fig_heat, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────────────────────
# PLATFORM TREND DETAIL
# ─────────────────────────────────────────────────────────────

st.subheader("📈 Platform Trend Explorer")

selected = st.selectbox(
    "Select Platform",
    sorted(df["platform"].dropna().unique())
)

trend = df[df["platform"] == selected]

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=trend["measurement_date"],
    y=trend["block_rate"] * 100,
    name="Block Rate",
    line=dict(width=2)
))

fig2.add_trace(go.Scatter(
    x=trend["measurement_date"],
    y=trend["platform_pressure_score"],
    name="Pressure Score",
    yaxis="y2"
))

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    yaxis=dict(title="Block %"),
    yaxis2=dict(overlaying="y", side="right", title="Pressure"),
    legend=dict(orientation="h"),
)

st.plotly_chart(fig2, use_container_width=True)
