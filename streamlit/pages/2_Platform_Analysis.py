import streamlit as st
import duckdb
import plotly.express as px

st.title("Platform Analysis: Kenya vs World")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties").df()

kenya = df[df['country'].str.upper() == 'KENYA']
global_df = df.groupby("platform").agg({"takedown_requests":"sum"}).reset_index()

fig_kenya = px.bar(kenya, x="platform", y="takedown_requests", color="reason",
                   title="Kenya Takedown Requests by Platform")
st.plotly_chart(fig_kenya, use_container_width=True)

fig_global = px.bar(global_df, x="platform", y="takedown_requests",
                    title="Global Takedown Requests by Platform")
st.plotly_chart(fig_global, use_container_width=True)
