import streamlit as st
import duckdb
import plotly.express as px

st.title("Fatalities & Civil Liberties Risks in Kenya")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

fig = px.bar(df, x="period", y="fatalities", title="Fatalities in Kenya")
st.plotly_chart(fig, use_container_width=True)

fig2 = px.line(df, x="period", y="takedown_requests", title="Takedown Requests Over Time")
st.plotly_chart(fig2, use_container_width=True)
