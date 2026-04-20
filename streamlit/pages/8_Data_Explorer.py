# pages/8_Data_Explorer.py

import re
import streamlit as st
import pandas as pd
import plotly.express as px

from utils.bq_client import run_query, table, PALETTE


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Data Explorer · Observatory",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Data Explorer (Hardened)")
st.caption("Safe SQL sandbox over curated civil-liberties marts")


# ─────────────────────────────────────────────
# SAFETY LAYER
# ─────────────────────────────────────────────

DANGEROUS_SQL = re.compile(
    r"\b(DELETE|DROP|INSERT|UPDATE|ALTER|TRUNCATE|CREATE|MERGE)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str):
    if DANGEROUS_SQL.search(sql):
        raise ValueError("Only SELECT queries are allowed")


def enforce_limit(sql: str, limit: int) -> str:
    sql = sql.strip().rstrip(";")

    if re.search(r"\blimit\s+\d+", sql, re.IGNORECASE):
        return sql

    return f"{sql}\nLIMIT {limit}"


def safe_run(sql: str) -> pd.DataFrame:
    validate_sql(sql)
    return run_query(sql)


# ─────────────────────────────────────────────
# TABLE WHITELIST (MART-ALIGNED)
# ─────────────────────────────────────────────

TABLES = [
    "civil_liberties_mart",
    "fact_takedown_requests",
    "fact_takedown_trends",
    "fact_conflict_events",
    "fact_platform_blocking_summary",
    "fact_censorship_measurements",
]


# ─────────────────────────────────────────────
# PRESETS
# ─────────────────────────────────────────────

PRESETS = {
    "Daily blocking rate": f"""
        SELECT
            measurement_date,
            block_rate,
            blocked_tests,
            conflict_events
        FROM {table("civil_liberties_mart")}
        ORDER BY measurement_date DESC
        LIMIT 100
    """,

    "Suppression windows overview": f"""
        SELECT
            measurement_date,
            suppression_window,
            conflict_events,
            block_rate
        FROM {table("civil_liberties_mart")}
        ORDER BY measurement_date DESC
        LIMIT 200
    """,

    "Takedown pressure trend": f"""
        SELECT *
        FROM {table("fact_takedown_trends")}
        ORDER BY year_month DESC
        LIMIT 200
    """,

    "Conflict intensity sample": f"""
        SELECT *
        FROM {table("fact_conflict_events")}
        ORDER BY event_count DESC
        LIMIT 200
    """
}


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 📦 Allowed Tables")

    for t in TABLES:
        st.code(t)

    st.divider()

    preset = st.selectbox("Load preset", list(PRESETS.keys()))


# ─────────────────────────────────────────────
# QUERY INPUT
# ─────────────────────────────────────────────

sql = st.text_area(
    "SQL Query (SELECT only)",
    value=PRESETS[preset],
    height=180
)

limit = st.slider("Row limit fallback", 10, 2000, 500)


# ─────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────

if st.button("▶ Run Query"):

    try:
        final_sql = enforce_limit(sql, limit)
        df = safe_run(final_sql)

        if df is None or df.empty:
            st.warning("No results returned")
            st.stop()

        st.success(f"{len(df):,} rows returned")

        st.dataframe(df, use_container_width=True)

        # ─────────────────────────────────────────
        # AUTO VISUALIZATION (SAFE)
        # ─────────────────────────────────────────

        num_cols = df.select_dtypes(include="number").columns.tolist()
        all_cols = df.columns.tolist()

        if num_cols and all_cols:

            st.divider()
            st.subheader("📊 Auto Visualization")

            x = st.selectbox("X axis", all_cols)
            y = st.selectbox("Y axis", num_cols)

            fig = px.line(df, x=x, y=y)

            fig.update_layout(
                plot_bgcolor="#0D0D0F",
                paper_bgcolor="#0D0D0F",
                font_color="#E8E6DF",
                margin=dict(l=10, r=10, t=20, b=10),
            )

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Query failed: {str(e)}")

else:
    st.info("Run a query or select a preset to begin")
