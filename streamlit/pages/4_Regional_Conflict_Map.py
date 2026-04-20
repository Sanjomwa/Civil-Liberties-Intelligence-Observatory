import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE
from utils.schema import CIVIL_LIBERTIES_MART_SCHEMA
from utils.validate import validate_schema


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Regional Conflict Pressure",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Regional Conflict Pressure (Proxy View)")
st.caption("National-level conflict + censorship pressure signals (Kenya)")


# ─────────────────────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────────────────────

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


# ─────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            conflict_events,
            fatalities,
            block_rate,
            takedown_requests,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY measurement_date
    """)


df = load_data(start_date, end_date)

validate_schema(df, CIVIL_LIBERTIES_MART_SCHEMA, "Regional Conflict Map")

df["conflict_events"] = df["conflict_events"].fillna(0)
df["fatalities"] = df["fatalities"].fillna(0)


# ─────────────────────────────────────────────────────────────
# SAFE KPI LAYER
# ─────────────────────────────────────────────────────────────

c1, c2, c3 = st.columns(3)

c1.metric("Total Conflict Events", f"{df['conflict_events'].sum():,.0f}")
c2.metric("Total Fatalities", f"{df['fatalities'].sum():,.0f}")
c3.metric("Avg Block Rate", f"{df['block_rate'].mean()*100:.2f}%")


# SAFE peak day handling
if not df.empty:
    peak_day = df.loc[df["conflict_events"].idxmax(), "measurement_date"]
    st.metric("Peak Pressure Day", peak_day.strftime("%Y-%m-%d"))
else:
    st.warning("No data available for selected range")

st.divider()


# ─────────────────────────────────────────────────────────────
# TIME SERIES VIEW
# ─────────────────────────────────────────────────────────────

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["conflict_events"],
    name="Conflict Events",
    line=dict(color=PALETTE["amber"], width=2)
))

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["fatalities"],
    name="Fatalities",
    line=dict(color=PALETTE["coral"], width=2),
    yaxis="y2"
))

fig.update_layout(
    title="National Conflict Pressure Over Time",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
    yaxis=dict(title="Conflict Events"),
    yaxis2=dict(overlaying="y", side="right", title="Fatalities"),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────
# SUPPRESSION WINDOW ANALYSIS
# ─────────────────────────────────────────────────────────────

st.subheader("🧠 Suppression Window Distribution")

sw = df.groupby("suppression_window", as_index=False).size()

fig2 = px.bar(
    sw,
    x="size",
    y="suppression_window",
    orientation="h",
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False,
)

st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# MONTHLY TREND
# ─────────────────────────────────────────────────────────────

df["year_month"] = pd.to_datetime(df["measurement_date"]).dt.to_period("M").astype(str)

monthly = df.groupby("year_month", as_index=False).agg({
    "conflict_events": "sum",
    "fatalities": "sum",
    "block_rate": "mean"
})

st.subheader("📊 Monthly Pressure Trend")

st.line_chart(
    monthly.set_index("year_month")[["conflict_events", "fatalities", "block_rate"]]
)
