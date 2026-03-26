import streamlit as st
import duckdb
import plotly.express as px

st.title("Reasons for Takedowns: Kenya vs World")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties").df()

kenya = df[df['country'].str.upper() == 'KENYA']
global_df = df.groupby("reason").agg({"takedown_requests":"sum"}).reset_index()

fig_kenya = px.pie(kenya, names="reason", values="takedown_requests", title="Kenya Reasons")
st.plotly_chart(fig_kenya, use_container_width=True)

fig_global = px.pie(global_df, names="reason", values="takedown_requests", title="Global Reasons")
st.plotly_chart(fig_global, use_container_width=True)
