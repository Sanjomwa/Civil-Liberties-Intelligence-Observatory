import streamlit as st
import duckdb
import plotly.express as px

st.title("Kenya Country Profile")

con = duckdb.connect(database=':memory:')
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")
df = con.execute("SELECT * FROM mart.civil_liberties WHERE UPPER(country)='KENYA'").df()

periods = st.sidebar.multiselect("Select periods", sorted(df['period'].unique()))
if periods:
    df = df[df['period'].isin(periods)]

fig_conflict = px.line(df, x="period", y="conflict_events", title="Conflict Events in Kenya")
st.plotly_chart(fig_conflict, use_container_width=True)

fig_censorship = px.line(df, x="period", y="censorship_tests", title="Censorship Tests in Kenya")
st.plotly_chart(fig_censorship, use_container_width=True)

fig_takedown = px.bar(df, x="platform", y="takedown_requests", color="reason",
                      title="Takedown Requests in Kenya by Platform & Reason")
st.plotly_chart(fig_takedown, use_container_width=True)
