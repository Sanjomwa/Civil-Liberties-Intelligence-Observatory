import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Civil Liberties Dashboard", layout="wide")

# Connect to DuckDB parquet mart
con = duckdb.connect(database=':memory:')
con.execute("INSTALL parquet; LOAD parquet;")
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")

# Load data
df = con.execute("SELECT * FROM mart.civil_liberties").df()

st.title("Civil Liberties & Censorship Analysis")

# Filters
countries = st.multiselect("Select countries", sorted(df['country'].dropna().unique()))
periods = st.multiselect("Select periods", sorted(df['period'].dropna().unique()))

filtered = df.copy()
if countries:
    filtered = filtered[filtered['country'].isin(countries)]
if periods:
    filtered = filtered[filtered['period'].isin(periods)]

# Charts
col1, col2 = st.columns(2)

with col1:
    fig_conflict = px.bar(filtered, x="period", y="conflict_events", color="country",
                          title="Conflict Events Over Time")
    st.plotly_chart(fig_conflict, use_container_width=True)

with col2:
    fig_censorship = px.line(filtered, x="period", y="censorship_tests", color="country",
                             title="Censorship Tests Over Time")
    st.plotly_chart(fig_censorship, use_container_width=True)

st.subheader("Takedown Requests by Platform")
fig_takedown = px.bar(filtered, x="platform", y="takedown_requests", color="reason",
                      title="Takedown Requests by Platform & Reason")
st.plotly_chart(fig_takedown, use_container_width=True)
