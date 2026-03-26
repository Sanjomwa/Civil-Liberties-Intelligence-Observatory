import streamlit as st
import duckdb
import plotly.graph_objects as go

st.title("Conflict vs Censorship Trends in Kenya")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

fig = go.Figure()
fig.add_trace(go.Scatter(x=df['period'], y=df['conflict_events'], name="Conflict Events", mode="lines"))
fig.add_trace(go.Scatter(x=df['period'], y=df['censorship_tests'], name="Censorship Tests", mode="lines", yaxis="y2"))

fig.update_layout(
    title="Conflict vs Censorship in Kenya",
    yaxis=dict(title="Conflict Events"),
    yaxis2=dict(title="Censorship Tests", overlaying="y", side="right")
)
st.plotly_chart(fig, use_container_width=True)
