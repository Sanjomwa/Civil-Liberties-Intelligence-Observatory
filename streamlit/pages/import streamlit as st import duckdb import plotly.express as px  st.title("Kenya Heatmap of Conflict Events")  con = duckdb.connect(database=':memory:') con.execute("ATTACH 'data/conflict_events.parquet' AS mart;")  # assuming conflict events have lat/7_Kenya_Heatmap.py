import streamlit as st
import duckdb
import plotly.express as px

st.title("Kenya Heatmap of Conflict Events")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/conflict_events.parquet' AS mart;")  # assuming conflict events have lat/lon
df = con.execute("SELECT * FROM mart.conflict_events WHERE UPPER(country)='KENYA'").df()

fig = px.density_mapbox(df, lat="latitude", lon="longitude", z="event_count",
                        radius=10, center=dict(lat=-0.0236, lon=37.9062), zoom=5,
                        mapbox_style="carto-positron", title="Conflict Event Heatmap in Kenya")
st.plotly_chart(fig, use_container_width=True)
