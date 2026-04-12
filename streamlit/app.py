"""
app.py — Kenya Civil Liberties & Censorship Observatory
Landing page: headline KPIs, suppression timeline, quick navigation.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.bq_client import run_query, table, PALETTE, SUPPRESSION_COLORS

st.set_page_config(
    page_title="Kenya Civil Liberties Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3 { font-family: 'Space Mono', monospace; }

.kpi-card {
    background: #16161A;
    border: 1px solid #2A2A2F;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 0.5rem;
}
.kpi-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6B6966;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #E8E6DF;
    line-height: 1;
}
.kpi-delta {
    font-size: 0.75rem;
    color: #6B6966;
    margin-top: 0.3rem;
}
.kpi-accent { color: #E8593C; }
.observatory-header {
    border-left: 3px solid #E8593C;
    padding-left: 1rem;
    margin-bottom: 2rem;
}
.alert-box {
    background: rgba(232, 89, 60, 0.08);
    border: 1px solid rgba(232, 89, 60, 0.3);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔭 Observatory")
    st.markdown("**Kenya Civil Liberties**  \n**& Censorship Monitor**")
    st.divider()
    st.markdown("**Data scope**")
    st.markdown("📅 Jun 2023 – Jun 2025")
    st.markdown("🇰🇪 Kenya only")
    st.divider()
    st.markdown("**Sources**")
    st.markdown("- OONI (censorship)")
    st.markdown("- Google Transparency")
    st.markdown("- Lumen (takedowns)")
    st.markdown("- ACLED (conflict)")
    st.divider()
    st.caption("DEZoomcamp 2026 Final Project")

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="observatory-header">
  <h1 style="margin:0;font-size:1.6rem;">KENYA CIVIL LIBERTIES &<br>CENSORSHIP OBSERVATORY</h1>
  <p style="color:#6B6966;margin:0.3rem 0 0;font-size:0.85rem;font-family:'DM Sans',sans-serif;">
    Tracking internet censorship, content removal, and civil unrest · Jun 2023 – Jun 2025
  </p>
</div>
""", unsafe_allow_html=True)

# ── Load KPI data ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_kpis():
    return run_query(f"""
        SELECT
            COUNT(*)                                AS total_measurements,
            COUNTIF(is_blocked)                     AS total_blocked,
            COUNTIF(is_confirmed_block)             AS confirmed_blocks,
            COUNTIF(blocked_on_protest_day)         AS blocked_on_protest_day,
            ROUND(SAFE_DIVIDE(
                COUNTIF(is_blocked), COUNT(*)
            ) * 100, 1)                             AS overall_blocking_rate,
            COUNT(DISTINCT measurement_date)        AS days_monitored,
            COUNT(DISTINCT platform)                AS platforms_tested
        FROM {table('civil_liberties_mart')}
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_suppression_timeline():
    return run_query(f"""
        SELECT
            measurement_date,
            suppression_window_type,
            COUNT(*)                                AS measurement_count,
            COUNTIF(is_blocked)                     AS blocked_count,
            SUM(protest_events_on_day)              AS protest_events,
            SUM(total_takedown_requests)            AS takedown_requests
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, suppression_window_type
        ORDER BY measurement_date
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_worst_days():
    return run_query(f"""
        SELECT
            measurement_date,
            political_context_flag,
            protest_season_flag,
            COUNTIF(is_blocked)                     AS blocks,
            COUNTIF(is_confirmed_block)             AS confirmed_blocks,
            MAX(protest_events_on_day)              AS protests,
            MAX(total_takedown_requests)            AS takedowns,
            MAX(censorship_intensity_score)         AS max_intensity,
            STRING_AGG(DISTINCT suppression_window_type, ' + ')  AS window_types
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, political_context_flag, protest_season_flag
        HAVING COUNTIF(is_blocked) > 0
        ORDER BY max_intensity DESC
        LIMIT 10
    """)

with st.spinner("Loading observatory data…"):
    kpis        = load_kpis()
    timeline_df = load_suppression_timeline()
    worst_days  = load_worst_days()

# ── KPI Cards ────────────────────────────────────────────────────────────────
k = kpis.iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Total Measurements</div>
      <div class="kpi-value">{int(k.total_measurements):,}</div>
      <div class="kpi-delta">{int(k.days_monitored)} days monitored</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Overall Blocking Rate</div>
      <div class="kpi-value kpi-accent">{k.overall_blocking_rate}%</div>
      <div class="kpi-delta">{int(k.total_blocked):,} blocked measurements</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Confirmed Blocks</div>
      <div class="kpi-value">{int(k.confirmed_blocks):,}</div>
      <div class="kpi-delta">High-confidence detections</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Blocked on Protest Day</div>
      <div class="kpi-value kpi-accent">{int(k.blocked_on_protest_day):,}</div>
      <div class="kpi-delta">Censorship × unrest overlap</div>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">Platforms Tested</div>
      <div class="kpi-value">{int(k.platforms_tested)}</div>
      <div class="kpi-delta">Across OONI, Google, Lumen</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Suppression Timeline ─────────────────────────────────────────────────────
st.markdown("#### Suppression Timeline")
st.caption("Daily measurement counts coloured by suppression window type")

fig = px.bar(
    timeline_df,
    x="measurement_date",
    y="measurement_count",
    color="suppression_window_type",
    color_discrete_map=SUPPRESSION_COLORS,
    labels={"measurement_date": "", "measurement_count": "Measurements",
            "suppression_window_type": "Type"},
    height=320,
)
fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(gridcolor="#2A2A2F", showgrid=False),
    yaxis=dict(gridcolor="#2A2A2F"),
    bargap=0.05,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Worst Days Table ─────────────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown("#### Highest Intensity Suppression Days")
    st.dataframe(
        worst_days.rename(columns={
            "measurement_date":     "Date",
            "political_context_flag": "Context",
            "blocks":               "Blocks",
            "confirmed_blocks":     "Confirmed",
            "protests":             "Protests",
            "takedowns":            "Takedowns",
            "max_intensity":        "Intensity Score",
        })[["Date","Context","Blocks","Confirmed","Protests","Takedowns","Intensity Score"]],
        use_container_width=True,
        hide_index=True,
    )

with col_r:
    st.markdown("#### Suppression Type Distribution")
    dist = timeline_df.groupby("suppression_window_type")["measurement_count"].sum().reset_index()
    fig2 = px.pie(
        dist,
        names="suppression_window_type",
        values="measurement_count",
        color="suppression_window_type",
        color_discrete_map=SUPPRESSION_COLORS,
        hole=0.55,
    )
    fig2.update_layout(
        plot_bgcolor="#0D0D0F",
        paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF",
        showlegend=True,
        legend=dict(orientation="v", font=dict(size=11)),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    fig2.update_traces(textinfo="percent", textfont_size=11)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.caption(
    "Data: OONI · Google Transparency · Lumen (mock) · ACLED  |  "
    "Built with Bruin, BigQuery, Terraform  |  DEZoomcamp 2026"
)
