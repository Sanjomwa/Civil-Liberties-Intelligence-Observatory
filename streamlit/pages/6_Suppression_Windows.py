"""
pages/6_Suppression_Windows.py
Deep dive into full suppression windows — blocking + protests + takedowns.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import html

from utils.bq_client import run_query, table, PALETTE, SUPPRESSION_COLORS


st.set_page_config(
    page_title="Suppression Windows · Observatory",
    page_icon="🚨",
    layout="wide"
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
st.caption("Days where blocking, protests, and takedowns overlap.")


# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_windows():
    return run_query(f"""
        SELECT
            DATE(measurement_date) AS measurement_date,
            political_context_flag,
            protest_season_flag,
            suppression_window_type,

            COUNT(*) AS measurements,
            COUNTIF(is_blocked) AS blocked,
            COUNTIF(is_confirmed_block) AS confirmed_blocked,

            MAX(censorship_intensity_score) AS max_intensity,
            MAX(protest_events_on_day) AS protests,
            MAX(fatalities_on_day) AS fatalities,
            MAX(total_takedown_requests) AS takedowns,

            STRING_AGG(DISTINCT test_category, ', ') AS categories_blocked,
            STRING_AGG(DISTINCT platform, ', ') AS platforms_blocked,

            MAX(counties_affected) AS counties_affected

        FROM {table('civil_liberties_mart')}
        GROUP BY 1,2,3,4
        ORDER BY max_intensity DESC
    """)


@st.cache_data(ttl=3600)
def load_intensity_distribution():
    return run_query(f"""
        SELECT
            suppression_window_type,
            ROUND(censorship_intensity_score, 1) AS intensity_bucket,
            COUNT(*) AS count
        FROM {table('civil_liberties_mart')}
        GROUP BY 1,2
        ORDER BY 1,2
    """)


@st.cache_data(ttl=3600)
def load_window_heatmap():
    return run_query(f"""
        SELECT
            year_month,
            suppression_window_type,
            COUNT(DISTINCT measurement_date) AS days,
            ROUND(AVG(censorship_intensity_score), 2) AS avg_intensity
        FROM {table('civil_liberties_mart')}
        GROUP BY 1,2
        ORDER BY 1
    """)


with st.spinner("Loading suppression window data…"):
    windows_df = load_windows()
    dist_df = load_intensity_distribution()
    heat_df = load_window_heatmap()


# ─────────────────────────────────────────────
# SAFETY NORMALIZATION
# ─────────────────────────────────────────────

if not windows_df.empty:
    windows_df["measurement_date"] = pd.to_datetime(
        windows_df["measurement_date"], errors="coerce"
    )

    windows_df["max_intensity"] = pd.to_numeric(
        windows_df["max_intensity"], errors="coerce"
    )


def safe(val, fmt=None):
    if val is None or pd.isna(val):
        return "—"
    return fmt.format(val) if fmt else val


# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

full_suppress = windows_df[
    windows_df["suppression_window_type"] == "Full Suppression Window"
]

block_protest = windows_df[
    windows_df["suppression_window_type"] == "Blocking + Protest Day"
]


# ─────────────────────────────────────────────
# KPI
# ─────────────────────────────────────────────

full_mean = full_suppress["max_intensity"].mean() if not full_suppress.empty else None

c1, c2, c3, c4 = st.columns(4)

c1.metric("Full Suppression Window days", len(full_suppress))
c2.metric("Blocking + Protest days", len(block_protest))

c3.metric(
    "Peak intensity score",
    safe(windows_df["max_intensity"].max(), "{:.2f}")
)

c4.metric(
    "Avg intensity — full windows",
    safe(full_mean, "{:.2f}")
)

st.divider()


# ─────────────────────────────────────────────
# HEATMAP
# ─────────────────────────────────────────────

st.markdown("#### Suppression Window Type × Month")

pivot = heat_df.pivot_table(
    index="suppression_window_type",
    columns="year_month",
    values="days",
    aggfunc="sum",
    fill_value=0
)

order = [
    "Full Suppression Window",
    "Blocking + Protest Day",
    "Blocking + Removal Activity",
    "Blocking Only",
    "No Suppression Signal",
]

pivot = pivot.reindex([x for x in order if x in pivot.index])

fig = go.Figure(go.Heatmap(
    z=pivot.values,
    x=pivot.columns.astype(str),
    y=pivot.index.astype(str),
    colorscale=[[0, "#16161A"], [0.5, "#993C1D"], [1, "#E8593C"]],
    text=[[str(int(v)) if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    showscale=True,
))

fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=300,
    margin=dict(l=220, r=20, t=20, b=80),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# INTENSITY
# ─────────────────────────────────────────────

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Intensity Distribution")

    fig_dist = px.box(
        windows_df,
        x="suppression_window_type",
        y="max_intensity",
        color="suppression_window_type",
        color_discrete_map=SUPPRESSION_COLORS
    )

    fig_dist.update_layout(
        showlegend=False,
        plot_bgcolor="#0D0D0F",
        paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF",
    )

    st.plotly_chart(fig_dist, use_container_width=True)


with c2:
    st.markdown("#### Intensity Timeline")

    daily = windows_df.groupby("measurement_date")["max_intensity"].max().reset_index()

    fig_line = go.Figure(go.Scatter(
        x=daily["measurement_date"],
        y=daily["max_intensity"],
        fill="tozeroy",
        line=dict(color=PALETTE["coral"])
    ))

    fig_line.update_layout(
        plot_bgcolor="#0D0D0F",
        paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF",
        height=340,
    )

    st.plotly_chart(fig_line, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────
# FULL WINDOWS
# ─────────────────────────────────────────────

st.markdown("#### Full Suppression Windows")

if full_suppress.empty:
    st.info("No full suppression windows detected.")

else:
    for _, row in full_suppress.head(20).iterrows():

        platforms = html.escape(str(row.platforms_blocked or "—"))
        categories = html.escape(str(row.categories_blocked or "—"))

        st.markdown(f"""
        <div class="window-card">
            <div class="window-date">
                📅 {row.measurement_date} · Intensity {safe(row.max_intensity, "{:.2f}")}
            </div>

            <div style="margin-top:0.4rem;color:#E8E6DF;">
                🔴 {safe(row.protests)} protests |
                💀 {safe(row.fatalities)} fatalities |
                📋 {safe(row.takedowns)} takedowns
            </div>

            <div class="window-context">
                Context: {html.escape(str(row.political_context_flag))} · {html.escape(str(row.protest_season_flag))}<br>
                Platforms: {platforms}<br>
                Categories: {categories}
            </div>
        </div>
        """, unsafe_allow_html=True)


st.divider()


# ─────────────────────────────────────────────
# TABLE
# ─────────────────────────────────────────────

st.markdown("#### All Suppression Events")

st.dataframe(
    windows_df[
        [
            "measurement_date",
            "suppression_window_type",
            "max_intensity",
            "blocked",
            "protests",
            "fatalities",
            "takedowns",
            "political_context_flag",
            "categories_blocked"
        ]
    ],
    use_container_width=True,
    hide_index=True
)
