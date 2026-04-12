"""
pages/6_Suppression_Windows.py
Deep dive into "full suppression windows" — days where blocking,
protests, AND takedown activity coincided. The observatory's signature analysis.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.bq_client import run_query, table, PALETTE, SUPPRESSION_COLORS

st.set_page_config(page_title="Suppression Windows · Observatory", page_icon="🚨", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
.window-card {
    background: rgba(232,89,60,0.07);
    border: 1px solid rgba(232,89,60,0.25);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.window-date {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: #E8593C;
    letter-spacing: 0.1em;
}
.window-context {
    font-size: 0.8rem;
    color: #6B6966;
    margin-top: 0.2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("## 🚨 Suppression Windows")
st.caption(
    "Days where internet blocking, civil unrest, AND content removal activity "
    "all occurred simultaneously — the hardest evidence of coordinated suppression."
)

@st.cache_data(ttl=3600)
def load_windows():
    return run_query(f"""
        SELECT
            measurement_date,
            political_context_flag,
            protest_season_flag,
            suppression_window_type,
            COUNT(*)                                        AS measurements,
            COUNTIF(is_blocked)                            AS blocked,
            COUNTIF(is_confirmed_block)                    AS confirmed_blocked,
            MAX(censorship_intensity_score)                 AS max_intensity,
            MAX(protest_events_on_day)                     AS protests,
            MAX(fatalities_on_day)                         AS fatalities,
            MAX(total_takedown_requests)                   AS takedowns,
            STRING_AGG(DISTINCT test_category, ', ')        AS categories_blocked,
            STRING_AGG(DISTINCT platform LIMIT 5, ', ')     AS platforms_blocked,
            MAX(counties_affected)                          AS counties_affected
        FROM {table('civil_liberties_mart')}
        GROUP BY measurement_date, political_context_flag, protest_season_flag, suppression_window_type
        ORDER BY max_intensity DESC
    """)

@st.cache_data(ttl=3600)
def load_intensity_distribution():
    return run_query(f"""
        SELECT
            suppression_window_type,
            ROUND(censorship_intensity_score, 1)            AS intensity_bucket,
            COUNT(*)                                        AS count
        FROM {table('civil_liberties_mart')}
        GROUP BY suppression_window_type, intensity_bucket
        ORDER BY suppression_window_type, intensity_bucket
    """)

@st.cache_data(ttl=3600)
def load_window_heatmap():
    return run_query(f"""
        SELECT
            year_month,
            suppression_window_type,
            COUNT(DISTINCT measurement_date)                AS days,
            ROUND(AVG(censorship_intensity_score), 2)       AS avg_intensity
        FROM {table('civil_liberties_mart')}
        GROUP BY year_month, suppression_window_type
        ORDER BY year_month
    """)

with st.spinner("Loading suppression window data…"):
    windows_df  = load_windows()
    dist_df     = load_intensity_distribution()
    heat_df     = load_window_heatmap()

# ── Summary KPIs ──────────────────────────────────────────────────────────────
full_suppress = windows_df[windows_df["suppression_window_type"] == "Full Suppression Window"]
block_protest = windows_df[windows_df["suppression_window_type"] == "Blocking + Protest Day"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Full Suppression Window days", f"{len(full_suppress)}")
c2.metric("Blocking + Protest days", f"{len(block_protest)}")
c3.metric(
    "Peak intensity score",
    f"{windows_df['max_intensity'].max():.2f}",
    help="0–1 scale: 1 = blocking + protest + confirmed block simultaneously",
)
c4.metric(
    "Avg intensity — full windows",
    f"{full_suppress['max_intensity'].mean():.2f}" if not full_suppress.empty else "—",
)

st.divider()

# ── Month × window type heatmap ───────────────────────────────────────────────
st.markdown("#### Suppression Window Type × Month — Day Count Heatmap")

pivot = heat_df.pivot(
    index="suppression_window_type",
    columns="year_month",
    values="days",
).fillna(0)

type_order = [
    "Full Suppression Window",
    "Blocking + Protest Day",
    "Blocking + Removal Activity",
    "Blocking Only",
    "No Suppression Signal",
]
pivot = pivot.reindex([t for t in type_order if t in pivot.index])

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale=[
        [0.0, "#16161A"],
        [0.3, "#4A1B0C"],
        [0.7, "#993C1D"],
        [1.0, "#E8593C"],
    ],
    text=[[str(int(v)) if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}", textfont=dict(size=10),
    showscale=True,
    colorbar=dict(title="Days", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
))
fig_heat.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", height=280,
    margin=dict(l=230, r=20, t=20, b=80),
    xaxis=dict(tickangle=45, tickfont=dict(size=8)),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Intensity distribution ────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Intensity Score Distribution by Window Type")
    fig_dist = px.box(
        windows_df,
        x="suppression_window_type", y="max_intensity",
        color="suppression_window_type",
        color_discrete_map=SUPPRESSION_COLORS,
        labels={"suppression_window_type":"","max_intensity":"Intensity score"},
        height=340,
    )
    fig_dist.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", showlegend=False,
        margin=dict(l=0,r=0,t=20,b=80),
        xaxis=dict(tickangle=20, tickfont=dict(size=9), showgrid=False),
        yaxis=dict(gridcolor="#2A2A2F"),
    )
    st.plotly_chart(fig_dist, use_container_width=True)

with c2:
    st.markdown("#### Suppression Timeline — Intensity Score")
    daily_intensity = windows_df.groupby("measurement_date")["max_intensity"].max().reset_index()
    daily_intensity = daily_intensity.sort_values("measurement_date")

    fig_int = go.Figure(go.Scatter(
        x=daily_intensity["measurement_date"],
        y=daily_intensity["max_intensity"],
        fill="tozeroy",
        fillcolor="rgba(232,89,60,0.15)",
        line=dict(color=PALETTE["coral"], width=1.2),
        mode="lines",
    ))
    fig_int.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", height=340,
        margin=dict(l=0,r=0,t=20,b=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#2A2A2F", title="Intensity"),
    )
    st.plotly_chart(fig_int, use_container_width=True)

st.divider()

# ── Full Suppression Window incident cards ────────────────────────────────────
st.markdown("#### Full Suppression Window Incidents")
st.caption("Days with simultaneous blocking + protest + takedown activity — sorted by severity")

if full_suppress.empty:
    st.info("No Full Suppression Windows detected in current data range.")
else:
    for _, row in full_suppress.head(20).iterrows():
        st.markdown(f"""
        <div class="window-card">
          <div class="window-date">📅 {row.measurement_date} &nbsp;·&nbsp;
            Intensity: <strong>{row.max_intensity:.2f}</strong> &nbsp;·&nbsp;
            {int(row.blocked)} measurements blocked
          </div>
          <div style="margin-top:0.4rem;font-size:0.85rem;color:#E8E6DF;">
            🔴 <strong>{int(row.protests or 0)}</strong> protest events &nbsp;|&nbsp;
            💀 <strong>{int(row.fatalities or 0)}</strong> fatalities &nbsp;|&nbsp;
            📋 <strong>{int(row.takedowns or 0)}</strong> takedown requests
          </div>
          <div class="window-context">
            Context: {row.political_context_flag} · {row.protest_season_flag}<br>
            Platforms: {row.platforms_blocked or "—"}<br>
            Counties: {row.counties_affected or "—"}
          </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.markdown("#### All Suppression Events — Sortable Table")
st.dataframe(
    windows_df[[
        "measurement_date","suppression_window_type","max_intensity",
        "blocked","protests","fatalities","takedowns","political_context_flag","categories_blocked"
    ]].rename(columns={
        "measurement_date":"Date","suppression_window_type":"Type","max_intensity":"Intensity",
        "blocked":"Blocked","protests":"Protests","fatalities":"Fatalities",
        "takedowns":"Takedowns","political_context_flag":"Period","categories_blocked":"Categories",
    }),
    use_container_width=True, hide_index=True,
)
