# pages/4_Regional_Conflict_Map.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE

st.set_page_config(
    page_title="Regional Pressure Overview",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Regional Conflict Pressure (Proxy View)")
st.caption("Kenya-wide temporal and political pressure distribution (NO county-level ACLED data in mart)")

# ─────────────────────────────────────────────────────────────
# GLOBAL FILTERS
# ─────────────────────────────────────────────────────────────

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


# ─────────────────────────────────────────────────────────────
# DATA LOAD (ONLY APPROVED MART)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            conflict_events,
            fatalities,
            block_rate,
            political_context_flag,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY measurement_date
    """)


df = load_data(start_date, end_date)


# ─────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Conflict Events", f"{df['conflict_events'].sum():,.0f}")
c2.metric("Total Fatalities", f"{df['fatalities'].sum():,.0f}")
c3.metric("Avg Block Rate", f"{df['block_rate'].mean()*100:.2f}%")
c4.metric("Peak Pressure Day", df.loc[df["conflict_events"].idxmax(), "measurement_date"].strftime("%Y-%m-%d"))

st.divider()


# ─────────────────────────────────────────────────────────────
# TIME SERIES PRESSURE VIEW
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
# BLOCK RATE CONTEXT VIEW
# ─────────────────────────────────────────────────────────────

st.subheader("🧠 Political Context vs Pressure")

context = df.groupby("political_context_flag", as_index=False).agg({
    "conflict_events": "mean",
    "block_rate": "mean",
    "fatalities": "mean"
})

fig2 = px.bar(
    context.sort_values("conflict_events"),
    x="conflict_events",
    y="political_context_flag",
    orientation="h",
    color="block_rate",
    color_continuous_scale="Reds",
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
)

st.plotly_chart(fig2, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────────────────────
# SUPPRESSION WINDOW DISTRIBUTION
# ─────────────────────────────────────────────────────────────

st.subheader("🧠 Suppression Window Distribution")

sw = df.groupby("suppression_window", as_index=False).size()

fig3 = px.bar(
    sw,
    x="size",
    y="suppression_window",
    orientation="h",
)

fig3.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False,
)

st.plotly_chart(fig3, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────────────────────
# MONTHLY INTENSITY TREND
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
