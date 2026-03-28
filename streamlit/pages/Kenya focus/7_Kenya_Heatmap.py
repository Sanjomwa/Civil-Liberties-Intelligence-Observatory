import streamlit as st
import duckdb
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

st.title("Kenya Heatmap of Conflict Events")

# Load conflict events (must include lat/lon)
con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/conflict_events.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.conflict_events WHERE UPPER(country)='KENYA'").df()

# Load Kenya boundary (GeoJSON or shapefile converted to GeoJSON)
kenya_boundary = gpd.read_file("data/kenya_boundary.geojson")

# Create density heatmap
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

# Overlay Kenya boundary outline
boundary_coords = kenya_boundary.geometry.iloc[0].exterior.coords
lats, lons = zip(*boundary_coords)

fig.add_trace(go.Scattermapbox(
    lat=lats,
    lon=lons,
    mode="lines",
    line=dict(width=2, color="black"),
    name="Kenya Boundary"
))

st.plotly_chart(fig, use_container_width=True)
