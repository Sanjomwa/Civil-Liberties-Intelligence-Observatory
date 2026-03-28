import streamlit as st
import duckdb
import plotly.express as px

st.title("Global Heatmap of Conflict Events")

# Load global conflict events (must include lat/lon)
con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/conflict_events.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.conflict_events").df()

# Aggregate by country for leaders/losers
leaders = df.groupby("country").agg({"event_count":"sum"}).reset_index().sort_values("event_count", ascending=False).head(5)
losers = df.groupby("country").agg({"event_count":"sum"}).reset_index().sort_values("event_count", ascending=True).head(5)

st.subheader("Top 5 Countries (Leaders in Conflict Events)")
st.dataframe(leaders)

st.subheader("Bottom 5 Countries (Lowest Conflict Events)")
st.dataframe(losers)

# Global heatmap
fig = px.density_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    z="event_count",
    radius=8,
    center=dict(lat=0, lon=20),  # Africa-centered view
    zoom=1.5,
    mapbox_style="carto-positron",
    title="Global Conflict Event Heatmap"
)

st.plotly_chart(fig, use_container_width=True)
