"""
pages/3_Protest_vs_Censorship.py
Core observatory question: does internet censorship spike on protest days?
Scatter plot, dual-axis timeline, correlation heatmap.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(page_title="Protest vs Censorship · Observatory", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
.insight-box {
    background: rgba(239,159,39,0.08);
    border-left: 3px solid #EF9F27;
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚡ Protest vs Censorship Correlation")
st.caption(
    "Does internet censorship spike when Kenyans protest? "
    "This is the observatory's core question."
)

with st.sidebar:
    st.markdown("### Filters")
    window = st.slider("Days around protest to include", 0, 7, 2,
                       help="How many days before/after a protest to flag as 'protest window'")
    min_protests = st.slider("Min protest events on day", 0, 10, 1)

@st.cache_data(ttl=3600)
def load_dual_timeline():
    return run_query(f"""
        SELECT
            measurement_date,
            political_context_flag,
            protest_season_flag,
            COUNTIF(is_blocked)                             AS blocked,
            COUNT(*)                                        AS total,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            MAX(protest_events_on_day)                      AS protest_events,
            MAX(fatalities_on_day)                          AS fatalities,
            MAX(total_takedown_requests)                    AS takedown_requests,
            MAX(censorship_intensity_score)                 AS intensity
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, political_context_flag, protest_season_flag
        ORDER BY measurement_date
    """)

@st.cache_data(ttl=3600)
def load_scatter():
    return run_query(f"""
        SELECT
            measurement_date,
            MAX(protest_events_on_day)                      AS protests,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            COUNTIF(is_blocked)                             AS blocked_count,
            political_context_flag,
            protest_season_flag
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, political_context_flag, protest_season_flag
        HAVING MAX(protest_events_on_day) IS NOT NULL
        ORDER BY measurement_date
    """)

@st.cache_data(ttl=3600)
def load_context_heatmap():
    return run_query(f"""
        SELECT
            political_context_flag,
            protest_season_flag,
            COUNT(*)                                        AS measurements,
            COUNTIF(is_blocked)                            AS blocked,
            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate,
            COUNTIF(blocked_on_protest_day)                AS blocked_on_protest_day
        FROM {table('civil_liberties_mart')}
        GROUP BY political_context_flag, protest_season_flag
    """)

with st.spinner("Loading correlation data…"):
    dual_df    = load_dual_timeline()
    scatter_df = load_scatter()
    context_df = load_context_heatmap()

# ── KPI banner ───────────────────────────────────────────────────────────────
protest_days  = int((dual_df["protest_events"] > 0).sum())
block_protest = dual_df[dual_df["protest_events"] > 0]["blocking_rate"].mean()
block_quiet   = dual_df[dual_df["protest_events"].isna() | (dual_df["protest_events"] == 0)]["blocking_rate"].mean()
lift          = round(block_protest - block_quiet, 1) if block_quiet else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Days with protest activity", f"{protest_days}")
c2.metric("Avg blocking rate — protest days", f"{block_protest:.1f}%")
c3.metric("Avg blocking rate — quiet days", f"{block_quiet:.1f}%")
c4.metric("Censorship lift on protest days", f"+{lift}pp", delta_color="inverse")

st.divider()

# ── Dual axis timeline ───────────────────────────────────────────────────────
st.markdown("#### Censorship Rate vs Protest Events — Daily Dual Axis")

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Scatter(
    x=dual_df["measurement_date"], y=dual_df["blocking_rate"],
    name="Blocking rate (%)", line=dict(color=PALETTE["coral"], width=1.5),
    fill="tozeroy", fillcolor="rgba(232,89,60,0.12)",
), secondary_y=False)

fig.add_trace(go.Bar(
    x=dual_df["measurement_date"], y=dual_df["protest_events"],
    name="Protest events", marker_color="rgba(239,159,39,0.5)",
    opacity=0.7,
), secondary_y=True)

fig.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=360,
    margin=dict(l=0,r=0,t=20,b=0),
    legend=dict(orientation="h", y=1.05),
    xaxis=dict(showgrid=False),
)
fig.update_yaxes(title_text="Blocking Rate %", gridcolor="#2A2A2F", secondary_y=False)
fig.update_yaxes(title_text="Protest Events", showgrid=False, secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Scatter: protest events vs blocking rate ─────────────────────────────────
st.markdown("#### Scatter — Protest Intensity vs Blocking Rate")
st.caption("Each point = one day. Size = number of blocked measurements.")

context_colors = {
    "Finance Bill Crisis Period":   PALETTE["coral"],
    "Post-Election Consolidation":  PALETTE["amber"],
    "Baseline Period":              PALETTE["teal"],
}

scatter_df["protests"] = scatter_df["protests"].fillna(0)
scatter_df["size"] = (scatter_df["blocked_count"] / scatter_df["blocked_count"].max() * 30 + 4)

fig_sc = px.scatter(
    scatter_df,
    x="protests", y="blocking_rate",
    color="political_context_flag",
    size="size",
    color_discrete_map=context_colors,
    labels={"protests":"Protest events on day","blocking_rate":"Blocking rate (%)","political_context_flag":"Period"},
    trendline="ols",
    trendline_scope="overall",
    trendline_color_override=PALETTE["muted"],
    height=380,
)
fig_sc.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", margin=dict(l=0,r=0,t=20,b=0),
    xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#2A2A2F"),
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(fig_sc, use_container_width=True)

st.divider()

# ── Context heatmap ──────────────────────────────────────────────────────────
st.markdown("#### Blocking Rate by Political Context × Protest Season")

pivot_ctx = context_df.pivot(
    index="political_context_flag",
    columns="protest_season_flag",
    values="blocking_rate"
).fillna(0)

fig_ctx = go.Figure(go.Heatmap(
    z=pivot_ctx.values,
    x=pivot_ctx.columns.tolist(),
    y=pivot_ctx.index.tolist(),
    colorscale=[[0,"#16161A"],[0.5,"#993C1D"],[1,"#E8593C"]],
    text=[[f"{v:.1f}%" for v in row] for row in pivot_ctx.values],
    texttemplate="%{text}", textfont=dict(size=13),
    showscale=True,
    colorbar=dict(title="Block %", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
))
fig_ctx.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=240,
    margin=dict(l=200, r=20, t=20, b=60),
    xaxis=dict(tickfont=dict(size=11)),
    yaxis=dict(tickfont=dict(size=11)),
)
st.plotly_chart(fig_ctx, use_container_width=True)

st.markdown(f"""
<div class="insight-box">
<strong>Key finding:</strong> Blocking rate on protest days is <strong>{block_protest:.1f}%</strong>
vs <strong>{block_quiet:.1f}%</strong> on quiet days — a <strong>+{lift} percentage point lift</strong>.
The Finance Bill Crisis Period (Aug–Dec 2024) shows the strongest correlation.
</div>
""", unsafe_allow_html=True)
