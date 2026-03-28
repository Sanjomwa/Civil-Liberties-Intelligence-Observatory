import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

st.title("Kenya vs Global Overview")

# Connect to mart
con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties").df()

# Kenya and Global aggregates
kenya_df = df[df['country'].str.upper() == 'KENYA']
global_df = df.copy()

summary = pd.DataFrame({
    "Metric": ["Takedown Requests", "Censorship Tests", "Conflict Events", "Fatalities"],
    "Kenya": [
        kenya_df["takedown_requests"].sum(),
        kenya_df["censorship_tests"].sum(),
        kenya_df["conflict_events"].sum(),
        kenya_df["fatalities"].sum()
    ],
    "Global": [
        global_df["takedown_requests"].sum(),
        global_df["censorship_tests"].sum(),
        global_df["conflict_events"].sum(),
        global_df["fatalities"].sum()
    ]
})

# Show summary table
st.subheader("Executive Snapshot")
st.dataframe(summary)

# Comparison chart
fig = px.bar(
    summary.melt(id_vars="Metric", value_vars=["Kenya","Global"]),
    x="Metric",
    y="value",
    color="variable",
    barmode="group",
    title="Kenya vs Global Civil Liberties Metrics"
)
st.plotly_chart(fig, use_container_width=True)

# Trend comparison
st.subheader("Trend Comparison Over Time")
kenya_trend = kenya_df.groupby("period").agg({
    "takedown_requests":"sum",
    "censorship_tests":"sum",
    "conflict_events":"sum",
    "fatalities":"sum"
}).reset_index()

global_trend = global_df.groupby("period").agg({
    "takedown_requests":"sum",
    "censorship_tests":"sum",
    "conflict_events":"sum",
    "fatalities":"sum"
}).reset_index()

fig_trend = px.line(
    pd.concat([
        kenya_trend.assign(scope="Kenya"),
        global_trend.assign(scope="Global")
    ]),
    x="period",
    y="takedown_requests",
    color="scope",
    title="Takedown Requests Trend: Kenya vs Global"
)
st.plotly_chart(fig_trend, use_container_width=True)
