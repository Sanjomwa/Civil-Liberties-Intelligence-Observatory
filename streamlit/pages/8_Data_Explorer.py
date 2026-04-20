"""
pages/8_Data_Explorer.py
Raw data explorer for Observatory mart tables.
Safe query execution, export, and auto visualization.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from utils.bq_client import run_query, table, PALETTE


st.set_page_config(
    page_title="Data Explorer · Observatory",
    page_icon="🔍",
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

.stTextArea textarea {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)


st.markdown("## 🔍 Data Explorer")
st.caption("Run SQL queries, explore mart tables, export results.")


# ─────────────────────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────────────────────

PRESETS = {
    "— Choose a preset —": "",
    "Daily blocking rate (last 30 days)": f"""
SELECT
    measurement_date,
    COUNT(*) AS total,
    COUNTIF(is_blocked) AS blocked,
    ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
FROM {table('civil_liberties_mart')}
GROUP BY measurement_date
ORDER BY measurement_date DESC
LIMIT 30
""".strip(),

    "Top 20 most-blocked platforms": f"""
SELECT
    platform,
    test_category,
    COUNT(*) AS total,
    COUNTIF(is_blocked) AS blocked,
    ROUND(SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) * 100, 1) AS blocking_rate
FROM {table('civil_liberties_mart')}
WHERE platform IS NOT NULL
GROUP BY platform, test_category
ORDER BY blocking_rate DESC
LIMIT 20
""".strip(),

    "Full Suppression Window incidents": f"""
SELECT
    measurement_date,
    political_context_flag,
    MAX(censorship_intensity_score) AS intensity,
    COUNTIF(is_blocked) AS blocked,
    MAX(protest_events_on_day) AS protests,
    MAX(total_takedown_requests) AS takedowns
FROM {table('civil_liberties_mart')}
WHERE suppression_window_type = 'Full Suppression Window'
GROUP BY measurement_date, political_context_flag
ORDER BY intensity DESC
""".strip(),

    "Monthly takedown trends": f"""
SELECT year_month, source, reason_group, total_requests, cumulative_requests
FROM {table('fact_takedown_trends')}
ORDER BY year_month, source
""".strip(),

    "Conflict events by county": f"""
SELECT
    county, region,
    SUM(event_count) AS events,
    SUM(fatalities) AS fatalities,
    COUNTIF(is_censorship_trigger_event) AS trigger_events
FROM {table('fact_conflict_events')}
GROUP BY county, region
ORDER BY events DESC
""".strip(),

    "Platform blocking heatmap data": f"""
SELECT year_month, platform, blocking_rate, total_measurements, blocked_count
FROM {table('fact_platform_blocking_summary')}
ORDER BY year_month, blocking_rate DESC
""".strip(),
}


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Available Tables")

    tables = [
        "civil_liberties_mart",
        "fact_censorship_measurements",
        "fact_censorship_impact",
        "fact_takedown_requests",
        "fact_takedown_trends",
        "fact_conflict_events",
        "fact_platform_blocking_summary",
        "dim_dates",
        "dim_regions",
        "dim_platforms",
        "dim_test_categories",
        "dim_reasons",
        "dim_event_types",
        "dim_requestors",
    ]

    for t in tables:
        st.markdown(f"`{t}`")


# ─────────────────────────────────────────────────────────────
# QUERY INPUT
# ─────────────────────────────────────────────────────────────

preset = st.selectbox("Load a preset query", list(PRESETS.keys()))

base_sql = PRESETS.get(preset, "")

default_sql = base_sql or f"""
SELECT *
FROM {table('civil_liberties_mart')}
LIMIT 100
""".strip()

query = st.text_area("SQL query", value=default_sql, height=180)

row_limit = st.slider("Row limit fallback", 10, 5000, 500)


def inject_limit(sql: str, limit: int) -> str:
    """Safely enforce LIMIT if not present."""
    clean = sql.strip().rstrip(";")
    if " limit " in clean.lower():
        return clean
    return f"{clean}\nLIMIT {limit}"


# ─────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────

if st.button("▶ Run Query", type="primary"):

    q = inject_limit(query, row_limit)

    with st.spinner("Running query on BigQuery…"):
        try:
            df = run_query(q)

            if df is None or df.empty:
                st.warning("Query returned no results.")
                st.stop()

            st.success(f"✅ {len(df):,} rows returned")

            # ── DOWNLOAD
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download CSV",
                data=csv,
                file_name="observatory_export.csv",
                mime="text/csv",
            )

            st.dataframe(df, use_container_width=True, hide_index=True)

            # ─────────────────────────────────────────────
            # AUTO CHART (SAFE)
            # ─────────────────────────────────────────────

            num_cols = df.select_dtypes(include="number").columns.tolist()
            str_cols = df.select_dtypes(include="object").columns.tolist()

            usable_x = list(df.columns)

            if len(num_cols) > 0 and len(usable_x) > 0:

                st.divider()
                st.markdown("#### Auto Visualization")

                c1, c2, c3 = st.columns(3)

                x_col = c1.selectbox("X axis", usable_x)
                y_col = c2.selectbox("Y axis", num_cols)
                chart_type = c3.selectbox("Chart type", ["Bar", "Line", "Scatter", "Area"])

                chart_map = {
                    "Bar": px.bar,
                    "Line": px.line,
                    "Scatter": px.scatter,
                    "Area": px.area,
                }

                fig = chart_map[chart_type](
                    df,
                    x=x_col,
                    y=y_col,
                    color_discrete_sequence=[PALETTE["coral"]],
                    height=380,
                )

                fig.update_layout(
                    plot_bgcolor="#0D0D0F",
                    paper_bgcolor="#0D0D0F",
                    font_color="#E8E6DF",
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor="#2A2A2F"),
                )

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Query failed: {str(e)}")

else:
    st.info("Select a preset or write SQL, then click ▶ Run Query.")


st.divider()

st.caption(
    "Queries run directly on BigQuery. "
    "Use LIMIT to control scan cost. Results cached for 1 hour."
)
