"""
pages/2_Platform_Blocking.py
Which apps, websites, and protocols are being blocked?
Bar charts, blocking rate trends, and platform heatmap.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(page_title="Platform Blocking · Observatory", page_icon="🔒", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔒 Platform Blocking Analysis")
st.caption("Which apps, websites, and circumvention tools are being blocked, and when?")

with st.sidebar:
    st.markdown("### Filters")
    category = st.multiselect(
        "Category",
        ["Website/DNS Blocking","Messaging App Blocking","Circumvention Tool Blocking","Other"],
        default=["Website/DNS Blocking","Messaging App Blocking","Circumvention Tool Blocking"],
    )
    top_n = st.slider("Top N platforms", 5, 30, 15)

cat_sql = "', '".join(category)

@st.cache_data(ttl=3600)
def load_platform_summary(cat_sql, top_n):
    return run_query(f"""
        SELECT
            platform,
            test_category,
            COUNT(*)                                        AS total,
            COUNTIF(is_blocked)                            AS blocked,
            COUNTIF(is_confirmed_block)                    AS confirmed,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
        FROM {table('civil_liberties_mart')}
        WHERE test_category IN ('{cat_sql}')
        GROUP BY platform, test_category
        ORDER BY blocking_rate DESC
        LIMIT {top_n}
    """)

@st.cache_data(ttl=3600)
def load_platform_trends():
    return run_query(f"""
        SELECT
            year_month,
            platform,
            blocking_rate,
            confirmed_blocking_rate,
            total_measurements,
            blocked_count
        FROM {table('fact_platform_blocking_summary')}
        ORDER BY year_month, blocking_rate DESC
    """)

@st.cache_data(ttl=3600)
def load_platform_heatmap():
    return run_query(f"""
        SELECT
            platform,
            year_month,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
        FROM {table('civil_liberties_mart')}
        WHERE platform IS NOT NULL
        GROUP BY platform, year_month
        HAVING COUNT(*) > 10
        ORDER BY platform, year_month
    """)

with st.spinner("Loading platform data…"):
    plat_df   = load_platform_summary(cat_sql, top_n)
    trends_df = load_platform_trends()
    heat_df   = load_platform_heatmap()

# ── Top blocked platforms ────────────────────────────────────────────────────
st.markdown("#### Top Blocked Platforms by Blocking Rate")

cat_colors = {
    "Website/DNS Blocking":         PALETTE["coral"],
    "Messaging App Blocking":       PALETTE["amber"],
    "Circumvention Tool Blocking":  PALETTE["purple"],
    "Other":                        PALETTE["gray"],
}

fig = px.bar(
    plat_df.sort_values("blocking_rate"),
    x="blocking_rate", y="platform",
    color="test_category",
    color_discrete_map=cat_colors,
    orientation="h",
    text="blocking_rate",
    labels={"blocking_rate":"Block %","platform":"","test_category":"Category"},
    height=max(300, top_n * 28),
)
fig.update_traces(texttemplate="%{text}%", textposition="outside")
fig.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", margin=dict(l=0,r=60,t=20,b=0),
    xaxis=dict(showgrid=False, range=[0, plat_df["blocking_rate"].max() * 1.15]),
    yaxis=dict(gridcolor="#2A2A2F"),
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Platform blocking heatmap ────────────────────────────────────────────────
st.markdown("#### Platform Blocking Rate Heatmap — Over Time")
st.caption("Month × platform. Darker = higher blocking rate that month.")

# Pivot: top 20 platforms by total blocking rate
top_platforms = (
    heat_df.groupby("platform")["blocking_rate"].mean()
    .sort_values(ascending=False).head(20).index.tolist()
)
heat_df_filt = heat_df[heat_df["platform"].isin(top_platforms)]
pivot = heat_df_filt.pivot(index="platform", columns="year_month", values="blocking_rate").fillna(0)

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale=[
        [0.0,  "#16161A"],
        [0.25, "#042C53"],
        [0.6,  "#185FA5"],
        [1.0,  "#E8593C"],
    ],
    text=[[f"{v:.0f}%" if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    textfont=dict(size=9),
    showscale=True,
    colorbar=dict(title="Block %", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
))
fig_heat.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=max(400, len(top_platforms) * 26),
    margin=dict(l=160, r=20, t=30, b=60),
    xaxis=dict(tickangle=45, tickfont=dict(size=9), side="bottom"),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Monthly trend lines for selected platform ────────────────────────────────
st.markdown("#### Monthly Blocking Trend — Select a Platform")

selected = st.selectbox(
    "Platform",
    sorted(trends_df["platform"].dropna().unique()),
)
trend_filt = trends_df[trends_df["platform"] == selected]

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=trend_filt["year_month"], y=trend_filt["blocking_rate"] * 100,
    name="All blocking", line=dict(color=PALETTE["coral"], width=2), mode="lines+markers",
))
fig_trend.add_trace(go.Scatter(
    x=trend_filt["year_month"], y=trend_filt["confirmed_blocking_rate"] * 100,
    name="Confirmed only", line=dict(color=PALETTE["amber"], width=2, dash="dot"),
    mode="lines+markers",
))
fig_trend.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=300,
    margin=dict(l=0,r=0,t=20,b=0),
    yaxis=dict(title="Block %", gridcolor="#2A2A2F"),
    xaxis=dict(title="", showgrid=False),
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(fig_trend, use_container_width=True)
