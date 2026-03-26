import streamlit as st
import duckdb

st.title("Global Leaders & Losers in Civil Liberties")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties").df()

leaders = df.groupby("country").agg({"takedown_requests":"sum"}).reset_index().sort_values("takedown_requests", ascending=False).head(5)
losers = df.groupby("country").agg({"takedown_requests":"sum"}).reset_index().sort_values("takedown_requests", ascending=True).head(5)

st.subheader("Top 5 Countries (Leaders)")
st.dataframe(leaders)

st.subheader("Bottom 5 Countries (Losers)")
st.dataframe(losers)
