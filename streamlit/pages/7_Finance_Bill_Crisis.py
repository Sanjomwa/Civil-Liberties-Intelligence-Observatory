"""
pages/7_Finance_Bill_Crisis.py
Deep dive into Jun–Dec 2024 Finance Bill protest period.
Kenya's most intense documented censorship window.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from utils.bq_client import run_query, table, PALETTE, STATUS_COLORS


st.set_page_config(
    page_title="Finance Bill Crisis · Observatory",
    page_icon="🔥",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1,h2,h3 {
    font-family: 'Space Mono', monospace;
}

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
    Jun–Dec 2024: Gen Z-led protests triggered Kenya's most significant
    documented internet interference period.
  </p>
</div>
""", unsafe_allow_html=True)


CRISIS_START = "2024-06-01"
CRISIS_END = "2024-12-31"


# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_crisis_vs_baseline():
    return run_query(f"""
        SELECT
            CASE
                WHEN measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'
                THEN 'Crisis Period (Jun–Dec 2024)'
                ELSE 'Baseline'
            END AS period,

            COUNT(*) AS measurements,
            COUNTIF(is_blocked) AS blocked,
            COUNTIF(is_confirmed_block) AS confirmed_blocked,

            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1)
                AS blocking_rate,

            COUNTIF(blocked_on_protest_day) AS blocked_protest_day,
            SUM(protest_events_on_day) AS total_protests,
            SUM(total_takedown_requests) AS total_takedowns

        FROM {table('civil_liberties_mart')}
        GROUP BY period
    """)


@st.cache_data(ttl=3600)
def load_crisis_daily():
    return run_query(f"""
        SELECT
            measurement_date,
            COUNTIF(is_blocked) AS blocked,
            COUNT(*) AS total,

            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1)
                AS blocking_rate,

            MAX(protest_events_on_day) AS protests,
            MAX(fatalities_on_day) AS fatalities,
            MAX(total_takedown_requests) AS takedowns,
            MAX(censorship_intensity_score) AS intensity

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
            COUNTIF(is_blocked) AS blocked,
            COUNT(*) AS total,

            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1)
                AS blocking_rate,

            COUNTIF(is_confirmed_block) AS confirmed

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
            FORMAT_DATE('%Y-W%V', measurement_date) AS iso_week,
            FORMAT_DATE('%a', measurement_date) AS dow_label,

            ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1)
                AS blocking_rate,

            MAX(protest_events_on_day) AS protests

        FROM {table('civil_liberties_mart')}
        WHERE measurement_date BETWEEN '{CRISIS_START}' AND '{CRISIS_END}'

        GROUP BY iso_week, dow_label
        ORDER BY iso_week, dow_label
    """)


# ─────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────

with st.spinner("Loading crisis analysis…"):
    compare_df = load_crisis_vs_baseline()
    daily_df = load_crisis_daily()
    platform_df = load_crisis_platforms()
    weekly_df = load_crisis_weekly_heatmap()


# ─────────────────────────────────────────────────────────────
# SAFE KPI EXTRACTION
# ─────────────────────────────────────────────────────────────

def safe_row(df: pd.DataFrame, col: str, match: str):
    if df.empty:
        return None
    match_df = df[df[col].str.contains(match, na=False)]
    return match_df.iloc[0] if not match_df.empty else None


crisis_row = safe_row(compare_df, "period", "Crisis")
baseline_row = safe_row(compare_df, "period", "Baseline")


# ─────────────────────────────────────────────────────────────
# KPI SECTION
# ─────────────────────────────────────────────────────────────

st.markdown("#### Crisis vs Baseline Comparison")

if crisis_row is not None and baseline_row is not None:
    delta = round(
        float(crisis_row["blocking_rate"] or 0)
        - float(baseline_row["blocking_rate"] or 0),
        1,
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Crisis blocking rate",
        f"{crisis_row['blocking_rate']}%",
        delta=f"{delta:+}pp vs baseline",
        delta_color="inverse",
    )
    c2.metric("Baseline blocking rate", f"{baseline_row['blocking_rate']}%")
    c3.metric("Crisis confirmed blocks", f"{int(crisis_row['confirmed_blocked'] or 0):,}")
    c4.metric("Crisis protest events", f"{int(crisis_row['total_protests'] or 0):,}")

st.divider()


# ─────────────────────────────────────────────────────────────
# DAILY CHART
# ─────────────────────────────────────────────────────────────

st.markdown("#### Daily Blocking Rate + Protest Events")

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Scatter(
        x=daily_df["measurement_date"],
        y=daily_df["blocking_rate"],
        name="Blocking rate (%)",
        fill="tozeroy",
        line=dict(color=PALETTE["coral"], width=1.8),
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Bar(
        x=daily_df["measurement_date"],
        y=daily_df["protests"],
        name="Protest events",
        marker_color="rgba(239,159,39,0.55)",
    ),
    secondary_y=True,
)

fig.add_trace(
    go.Scatter(
        x=daily_df["measurement_date"],
        y=daily_df["intensity"],
        name="Intensity score",
        line=dict(color=PALETTE["purple"], width=1, dash="dot"),
    ),
    secondary_y=False,
)

fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=380,
    margin=dict(l=0, r=0, t=20, b=0),
    legend=dict(orientation="h", y=1.06),
)

fig.update_yaxes(title_text="Blocking / Intensity", secondary_y=False)
fig.update_yaxes(title_text="Protests", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────
# WEEKLY HEATMAP
# ─────────────────────────────────────────────────────────────

st.markdown("#### Week × Day Blocking Heatmap")

pivot = weekly_df.pivot(
    index="dow_label",
    columns="iso_week",
    values="blocking_rate",
).fillna(0)

fig_wh = go.Figure(
    go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[[0, "#16161A"], [0.4, "#993C1D"], [1, "#E8593C"]],
        text=[[f"{v:.0f}%" if v > 0 else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
    )
)

fig_wh.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=240,
)

st.plotly_chart(fig_wh, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# PLATFORM BREAKDOWN
# ─────────────────────────────────────────────────────────────

st.markdown("#### Most Blocked Platforms")

fig_plat = px.bar(
    platform_df.sort_values("blocking_rate"),
    x="blocking_rate",
    y="platform",
    orientation="h",
    color="test_category",
    text="blocking_rate",
)

fig_plat.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=460,
)

fig_plat.update_traces(texttemplate="%{text}%")

st.plotly_chart(fig_plat, use_container_width=True)
