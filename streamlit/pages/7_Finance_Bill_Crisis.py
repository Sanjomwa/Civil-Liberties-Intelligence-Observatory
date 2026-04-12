"""
pages/7_Finance_Bill_Crisis.py
Deep dive into the Jun–Dec 2024 Finance Bill protest period —
Kenya's most intense documented censorship window.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.bq_client import run_query, table, PALETTE, STATUS_COLORS

st.set_page_config(page_title="Finance Bill Crisis · Observatory", page_icon="🔥", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
.crisis-banner {
    background: linear-gradient(135deg, rgba(232,89,60,0.12), rgba(239,159,39,0.06));
    border: 1px solid rgba(232,89,60,0.3);
    border-radius: 12px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="crisis-banner">
  <h2 style="margin:0;font-family:'Space Mono',monospace;font-size:1.2rem;">
    🔥 KENYA FINANCE BILL CRISIS — 2024
  </h2>
  <p style="margin:0.4rem 0 0;color:#6B6966;font-size:0.85rem;">
    Jun–Dec 2024: Gen Z-led protests against the Finance Bill triggered Kenya's most significant
    documented period of internet interference. This dashboard isolates that period for forensic analysis.
  </p>
</div>
""", unsafe_allow_html=True)

CRISIS_START = "2024-06-01"
CRISIS_END   = "2024-12-31"

@st.cache_data(ttl=3600)
def load_crisis_vs_baseline():
    return run_query(f"""
        SELECT
            CASE
                WHEN measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'
                THEN 'Crisis Period (Jun–Dec 2024)'
                ELSE 'Baseline'
            END                                         AS period,
            COUNT(*)                                    AS measurements,
            COUNTIF(is_blocked)                        AS blocked,
            COUNTIF(is_confirmed_block)                AS confirmed_blocked,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            COUNTIF(blocked_on_protest_day)            AS blocked_protest_day,
            SUM(protest_events_on_day)                 AS total_protests,
            SUM(total_takedown_requests)               AS total_takedowns
        FROM {table('civil_liberties_mart')}
        GROUP BY period
    """)

@st.cache_data(ttl=3600)
def load_crisis_daily():
    return run_query(f"""
        SELECT
            measurement_date,
            COUNTIF(is_blocked)                        AS blocked,
            COUNT(*)                                    AS total,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            MAX(protest_events_on_day)                 AS protests,
            MAX(fatalities_on_day)                     AS fatalities,
            MAX(total_takedown_requests)               AS takedowns,
            MAX(censorship_intensity_score)            AS intensity
        FROM {table('civil_liberties_mart')}
        WHERE measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'
        GROUP BY measurement_date
        ORDER BY measurement_date
    """)

@st.cache_data(ttl=3600)
def load_crisis_platforms():
    return run_query(f"""
        SELECT
            platform,
            test_category,
            COUNTIF(is_blocked)                        AS blocked,
            COUNT(*)                                    AS total,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            COUNTIF(is_confirmed_block)                AS confirmed
        FROM {table('civil_liberties_mart')}
        WHERE measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'
          AND platform IS NOT NULL
        GROUP BY platform, test_category
        HAVING COUNTIF(is_blocked) > 0
        ORDER BY blocking_rate DESC
        LIMIT 20
    """)

@st.cache_data(ttl=3600)
def load_crisis_weekly_heatmap():
    return run_query(f"""
        SELECT
            FORMAT_DATE('%Y-W%V', measurement_date)    AS iso_week,
            EXTRACT(DAYOFWEEK FROM measurement_date)   AS dow,
            FORMAT_DATE('%a', measurement_date)        AS dow_label,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            MAX(protest_events_on_day)                 AS protests
        FROM {table('civil_liberties_mart')}
        WHERE measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'
        GROUP BY iso_week, dow, dow_label
        ORDER BY iso_week, dow
    """)

with st.spinner("Loading crisis analysis…"):
    compare_df   = load_crisis_vs_baseline()
    daily_df     = load_crisis_daily()
    platform_df  = load_crisis_platforms()
    weekly_df    = load_crisis_weekly_heatmap()

# ── Crisis vs Baseline comparison ────────────────────────────────────────────
st.markdown("#### Crisis Period vs Baseline Comparison")

crisis_row   = compare_df[compare_df["period"].str.contains("Crisis")].iloc[0] if not compare_df[compare_df["period"].str.contains("Crisis")].empty else None
baseline_row = compare_df[compare_df["period"] == "Baseline"].iloc[0] if not compare_df[compare_df["period"] == "Baseline"].empty else None

if crisis_row is not None and baseline_row is not None:
    c1, c2, c3, c4 = st.columns(4)
    delta = round(float(crisis_row.blocking_rate) - float(baseline_row.blocking_rate), 1)
    c1.metric("Crisis blocking rate",   f"{crisis_row.blocking_rate}%",
              delta=f"{delta:+}pp vs baseline", delta_color="inverse")
    c2.metric("Baseline blocking rate", f"{baseline_row.blocking_rate}%")
    c3.metric("Crisis confirmed blocks",f"{int(crisis_row.confirmed_blocked):,}")
    c4.metric("Crisis protest events",  f"{int(crisis_row.total_protests or 0):,}")

st.divider()

# ── Dual-axis daily chart ────────────────────────────────────────────────────
st.markdown("#### Daily Blocking Rate + Protest Events — Crisis Period")

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(
    x=daily_df["measurement_date"], y=daily_df["blocking_rate"],
    name="Blocking rate (%)", fill="tozeroy",
    fillcolor="rgba(232,89,60,0.15)",
    line=dict(color=PALETTE["coral"], width=1.8),
), secondary_y=False)
fig.add_trace(go.Bar(
    x=daily_df["measurement_date"], y=daily_df["protests"],
    name="Protest events",
    marker_color="rgba(239,159,39,0.55)",
), secondary_y=True)
fig.add_trace(go.Scatter(
    x=daily_df["measurement_date"], y=daily_df["intensity"],
    name="Intensity score",
    line=dict(color=PALETTE["purple"], width=1, dash="dot"),
    mode="lines",
), secondary_y=False)
fig.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=380,
    margin=dict(l=0,r=0,t=20,b=0),
    legend=dict(orientation="h", y=1.06),
    xaxis=dict(showgrid=False),
)
fig.update_yaxes(title_text="Block rate / Intensity", gridcolor="#2A2A2F", secondary_y=False)
fig.update_yaxes(title_text="Protests", showgrid=False, secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Crisis weekly heatmap ────────────────────────────────────────────────────
st.markdown("#### Week × Day Blocking Rate Heatmap — Crisis Period")
st.caption("Which days of the week were most targeted during the Finance Bill protests?")

dow_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
pivot = weekly_df.pivot(index="dow_label", columns="iso_week", values="blocking_rate").fillna(0)
pivot = pivot.reindex([d for d in dow_order if d in pivot.index])

fig_wh = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale=[[0,"#16161A"],[0.4,"#993C1D"],[1,"#E8593C"]],
    text=[[f"{v:.0f}%" if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}", textfont=dict(size=9),
    showscale=True,
    colorbar=dict(title="Block %", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
))
fig_wh.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=240,
    margin=dict(l=50, r=20, t=20, b=80),
    xaxis=dict(tickangle=70, tickfont=dict(size=7)),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_wh, use_container_width=True)

st.divider()

# ── Crisis platform breakdown ────────────────────────────────────────────────
st.markdown("#### Most Blocked Platforms During Crisis")

cat_colors = {
    "Website/DNS Blocking":         PALETTE["coral"],
    "Messaging App Blocking":       PALETTE["amber"],
    "Circumvention Tool Blocking":  PALETTE["purple"],
    "Other":                        PALETTE["gray"],
}

fig_plat = px.bar(
    platform_df.sort_values("blocking_rate"),
    x="blocking_rate", y="platform",
    color="test_category", color_discrete_map=cat_colors,
    orientation="h", text="blocking_rate",
    labels={"blocking_rate":"Block %","platform":"","test_category":"Category"},
    height=460,
)
fig_plat.update_traces(texttemplate="%{text}%", textposition="outside")
fig_plat.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", margin=dict(l=0,r=60,t=20,b=0),
    xaxis=dict(showgrid=False),
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(fig_plat, use_container_width=True)
