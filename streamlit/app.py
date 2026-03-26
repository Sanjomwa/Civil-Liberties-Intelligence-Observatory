import streamlit as st
import duckdb
import pandas as pd

st.set_page_config(page_title="Civil Liberties & Censorship in Kenya", layout="wide")

# Connect to DuckDB parquet mart
con = duckdb.connect(database=':memory:')
con.execute("INSTALL parquet; LOAD parquet;")
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")

# Load mart data
df = con.execute("SELECT * FROM mart.civil_liberties").df()

# Default filter to Kenya
df = df[df['country'].str.upper() == 'KENYA']

st.title("Civil Liberties & Censorship Analysis in Kenya (June 2023–June 2026)")
st.write("This dashboard focuses on government takedown requests, censorship tests, and conflict events in Kenya.")

st.sidebar.header("Filters")
periods = st.sidebar.multiselect("Select periods", sorted(df['period'].unique()))

if periods:
    df = df[df['period'].isin(periods)]

st.dataframe(df.head())
