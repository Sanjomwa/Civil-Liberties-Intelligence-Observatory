import streamlit as st
import plotly.express as px
import duckdb

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

st.title("Kenya Country Profile")

fig = px.line(df, x="period", y="conflict_events", title="Conflict Events in Kenya")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(df, x="period", y="censorship_tests", title="Censorship Tests in Kenya")
st.plotly_chart(fig2, use_container_width=True)
