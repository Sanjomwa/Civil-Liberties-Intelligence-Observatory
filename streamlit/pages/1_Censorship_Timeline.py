"""
pages/1_Censorship_Timeline.py
Daily and monthly OONI blocking trends with calendar heatmap.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.bq_client import run_query, table, PALETTE, STATUS_COLORS

st.set_page_config(
    page_title="Censorship Timeline · Observatory",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📈 Censorship Timeline")
st.caption("OONI blocking measurements over time — daily trends, monthly heatmap, and status breakdown")

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    status_filter = st.multiselect(
        "Measurement status",
        ["ok", "anomaly", "confirmed", "failure"],
        default=["anomaly", "confirmed", "failure"],
    )
    category_filter = st.multiselect(
        "Test category",
        ["Website/DNS Blocking", "Messaging App Blocking",
         "Circumvention Tool Blocking", "Other"],
        default=["Website/DNS Blocking", "Messaging App Blocking",
                 "Circumvention Tool Blocking"],
    )
    granularity = st.radio("Time granularity", ["Daily", "Weekly", "Monthly"], index=2)

# ── Data ─────────────────────────────────────────────────────────────────────
status_sql   = "', '".join(status_filter)
category_sql = "', '".join(category_filter)

@st.cache_data(ttl=3600)
def load_daily(status_sql, category_sql):
    return run_query(f"""
        SELECT
            measurement_date,
            censorship_status,
            test_category,
            COUNT(*)                        AS measurements,
            COUNTIF(is_blocked)             AS blocked,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 2) AS blocking_pct
        FROM {table('civil_liberties_mart')}
        WHERE censorship_status IN ('{status_sql}')
          AND test_category IN ('{category_sql}')
        GROUP BY measurement_date, censorship_status, test_category
        ORDER BY measurement_date
    """)

@st.cache_data(ttl=3600)
def load_monthly_heatmap():
    return run_query(f"""
        SELECT
            year,
            month,
            month_name,
            year_month,
            COUNT(*)                        AS total,
            COUNTIF(is_blocked)             AS blocked,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
        FROM {table('civil_liberties_mart')}
        GROUP BY year, month, month_name, year_month
        ORDER BY year, month
    """)

@st.cache_data(ttl=3600)
def load_weekly_calendar():
    return run_query(f"""
        SELECT
            measurement_date,
            EXTRACT(WEEK FROM measurement_date)  AS week_num,
            EXTRACT(DAYOFWEEK FROM measurement_date) AS dow,
            year,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, week_num, dow, year
        ORDER BY measurement_date
    """)

with st.spinner("Loading timeline…"):
    daily_df    = load_daily(status_sql, category_sql)
    monthly_df  = load_monthly_heatmap()
    calendar_df = load_weekly_calendar()

# ── Main trend chart ─────────────────────────────────────────────────────────
st.markdown("#### Blocking Measurements Over Time")

if granularity == "Daily":
    agg = daily_df.groupby(["measurement_date","censorship_status"])["blocked"].sum().reset_index()
    fig = px.area(
        agg, x="measurement_date", y="blocked",
        color="censorship_status",
        color_discrete_map=STATUS_COLORS,
        labels={"measurement_date":"","blocked":"Blocked measurements","censorship_status":"Status"},
        height=340,
    )
elif granularity == "Weekly":
    agg = daily_df.copy()
    agg["week"] = pd.to_datetime(agg["measurement_date"]).dt.to_period("W").dt.start_time
    agg = agg.groupby(["week","censorship_status"])["blocked"].sum().reset_index()
    fig = px.bar(
        agg, x="week", y="blocked",
        color="censorship_status",
        color_discrete_map=STATUS_COLORS,
        labels={"week":"","blocked":"Blocked","censorship_status":"Status"},
        height=340,
    )
else:
    agg = daily_df.copy()
    agg["month"] = pd.to_datetime(agg["measurement_date"]).dt.to_period("M").dt.start_time
    agg = agg.groupby(["month","censorship_status"])["blocked"].sum().reset_index()
    fig = px.bar(
        agg, x="month", y="blocked",
        color="censorship_status",
        color_discrete_map=STATUS_COLORS,
        labels={"month":"","blocked":"Blocked","censorship_status":"Status"},
        height=340,
        barmode="stack",
    )

fig.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", margin=dict(l=0,r=0,t=20,b=0),
    legend=dict(orientation="h", y=1.05),
    xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#2A2A2F"),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Calendar heatmap (month × year) ─────────────────────────────────────────
st.markdown("#### Monthly Blocking Rate Heatmap")
st.caption("Each cell = % of measurements blocked that month. Darker red = higher censorship.")

pivot = monthly_df.pivot(index="year", columns="month_name", values="blocking_rate")
month_order = ["June","July","August","September","October","November",
               "December","January","February","March","April","May"]
pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=[str(y) for y in pivot.index.tolist()],
    colorscale=[
        [0.0, "#16161A"],
        [0.3, "#4A1B0C"],
        [0.6, "#993C1D"],
        [1.0, "#E8593C"],
    ],
    text=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    textfont=dict(size=11),
    showscale=True,
    colorbar=dict(title="Block %", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
    hoverongaps=False,
))
fig_heat.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=220,
    margin=dict(l=60, r=20, t=20, b=40),
    xaxis=dict(side="bottom", tickfont=dict(size=11)),
    yaxis=dict(tickfont=dict(size=11)),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Day-of-week heatmap ──────────────────────────────────────────────────────
st.markdown("#### Blocking Rate by Day of Week × Month")
st.caption("Do censorship spikes follow weekly protest rhythms?")

dow_labels = {1:"Sun",2:"Mon",3:"Tue",4:"Wed",5:"Thu",6:"Fri",7:"Sat"}
calendar_df["dow_label"] = calendar_df["dow"].map(dow_labels)
calendar_df["month_period"] = pd.to_datetime(calendar_df["measurement_date"]).dt.to_period("M").astype(str)

pivot2 = calendar_df.groupby(["month_period","dow_label"])["blocking_rate"].mean().reset_index()
pivot2 = pivot2.pivot(index="dow_label", columns="month_period", values="blocking_rate")
dow_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
pivot2 = pivot2.reindex([d for d in dow_order if d in pivot2.index])

fig_dow = go.Figure(go.Heatmap(
    z=pivot2.values,
    x=pivot2.columns.tolist(),
    y=pivot2.index.tolist(),
    colorscale=[
        [0.0, "#16161A"],
        [0.5, "#185FA5"],
        [1.0, "#E8593C"],
    ],
    text=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in pivot2.values],
    texttemplate="%{text}",
    textfont=dict(size=10),
    showscale=True,
    colorbar=dict(title="Block %", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
))
fig_dow.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=280,
    margin=dict(l=60, r=20, t=10, b=60),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
)
st.plotly_chart(fig_dow, use_container_width=True)

# ── Monthly table ────────────────────────────────────────────────────────────
st.divider()
st.markdown("#### Monthly Summary Table")
st.dataframe(
    monthly_df[["year_month","total","blocked","blocking_rate"]]
    .rename(columns={"year_month":"Month","total":"Total","blocked":"Blocked","blocking_rate":"Block %"}),
    use_container_width=True, hide_index=True,
)
