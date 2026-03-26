import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# Page setup
st.set_page_config(
    page_title="Civil Liberties & Censorship in Kenya",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title banner
st.title("🇰🇪 Civil Liberties & Censorship Analysis in Kenya (June 2023 – June 2026)")
st.markdown("""
This dashboard explores government takedown requests, censorship tests, and conflict events in Kenya,
with comparisons to global leaders and laggards.
""")

# Connect to mart
con = duckdb.connect(database=':memory:')
con.execute("INSTALL parquet; LOAD parquet;")
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")

# Load mart data
df = con.execute("SELECT * FROM mart.civil_liberties").df()

# Default filter to Kenya
kenya_df = df[df['country'].str.upper() == 'KENYA']

# Sidebar navigation
st.sidebar.header("📊 Dashboard Navigation")
st.sidebar.markdown("Use the sidebar to explore different dashboards:")

pages = [
    "Kenya Profile",
    "Platform Analysis",
    "Reasons for Takedowns",
    "Conflict vs Censorship",
    "Fatalities & Risks",
    "Global Leaders & Losers",
    "Kenya Heatmap"
]

choice = st.sidebar.radio("Select a dashboard", pages)

# Simple preview on landing page
if choice == "Kenya Profile":
    st.subheader("Quick Preview: Conflict Events in Kenya")
    fig = px.line(kenya_df, x="period", y="conflict_events", title="Conflict Events Over Time")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Platform Analysis":
    st.subheader("Quick Preview: Takedown Requests by Platform (Kenya)")
    fig = px.bar(kenya_df, x="platform", y="takedown_requests", color="reason",
                 title="Kenya Takedown Requests by Platform & Reason")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Reasons for Takedowns":
    st.subheader("Quick Preview: Reasons in Kenya")
    fig = px.pie(kenya_df, names="reason", values="takedown_requests", title="Reasons for Takedowns in Kenya")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Conflict vs Censorship":
    st.subheader("Quick Preview: Conflict vs Censorship")
    fig = px.line(kenya_df, x="period", y="censorship_tests", title="Censorship Tests Over Time")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Fatalities & Risks":
    st.subheader("Quick Preview: Fatalities in Kenya")
    fig = px.bar(kenya_df, x="period", y="fatalities", title="Fatalities Over Time")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Global Leaders & Losers":
    st.subheader("Quick Preview: Global Rankings")
    leaders = df.groupby("country").agg({"takedown_requests":"sum"}).reset_index().sort_values("takedown_requests", ascending=False).head(5)
    st.dataframe(leaders)

elif choice == "Kenya Heatmap":
    st.subheader("Quick Preview: Heatmap Placeholder")
    st.info("Heatmap of conflict events in Kenya will be shown here (requires lat/lon data).")
