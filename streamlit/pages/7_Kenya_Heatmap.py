import streamlit as st
import duckdb
import geopandas as gpd
import plotly.express as px

st.title("Kenya Heatmap of Conflict Events")

# Load conflict events (must include lat/lon)
con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/conflict_events.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.conflict_events WHERE UPPER(country)='KENYA'").df()

# Load Kenya boundary
kenya_boundary = gpd.read_file("data/kenya_boundary.geojson")

# Plot heatmap
fig = px.density_mapbox(
    df,
    lat="latitude",
    lon="longitude",
    z="event_count",
    radius=10,
    center=dict(lat=-0.0236, lon=37.9062),  # Kenya center
    zoom=5,
    mapbox_style="carto-positron",
    title="Conflict Event Heatmap in Kenya"
)

st.plotly_chart(fig, use_container_width=True)

# Show Kenya boundary outline
st.subheader("Kenya Boundary")
st.map(kenya_boundary)
