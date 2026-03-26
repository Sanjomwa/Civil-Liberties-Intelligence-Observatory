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
st.title("🇰🇪 Civil Liberties & Censorship Analysis (June 2023 – June 2026)")
st.markdown("""
Explore government takedown requests, censorship tests, and conflict events in Kenya,
with comparisons to global leaders and laggards.
""")

# Connect to mart
con = duckdb.connect(database=':memory:')
con.execute("INSTALL parquet; LOAD parquet;")
con.execute("ATTACH 'data/civil_liberties_mart.parquet' AS mart;")

# Load mart data
df = con.execute("SELECT * FROM mart.civil_liberties").df()

# Sidebar toggle
st.sidebar.header("⚙️ Settings")
view_mode = st.sidebar.radio("Select view mode:", ["Kenya", "Global"])

if view_mode == "Kenya":
    df_display = df[df['country'].str.upper() == 'KENYA']
else:
    df_display = df.copy()

# Sidebar navigation
st.sidebar.header("📊 Dashboard Navigation")
pages = [
    "Profile",
    "Platform Analysis",
    "Reasons for Takedowns",
    "Conflict vs Censorship",
    "Fatalities & Risks",
    "Leaders & Losers",
    "Heatmap"
]
choice = st.sidebar.radio("Select a dashboard", pages)

# Dashboard previews
if choice == "Profile":
    st.subheader(f"{view_mode} Profile")
    fig = px.line(df_display, x="period", y="conflict_events", color="country",
                  title=f"Conflict Events ({view_mode})")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Platform Analysis":
    st.subheader(f"Takedown Requests by Platform ({view_mode})")
    fig = px.bar(df_display, x="platform", y="takedown_requests", color="reason",
                 title=f"Takedown Requests by Platform ({view_mode})")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Reasons for Takedowns":
    st.subheader(f"Reasons for Takedowns ({view_mode})")
    fig = px.pie(df_display, names="reason", values="takedown_requests",
                 title=f"Reasons for Takedowns ({view_mode})")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Conflict vs Censorship":
    st.subheader(f"Conflict vs Censorship ({view_mode})")
    fig = px.line(df_display, x="period", y="censorship_tests", color="country",
                  title=f"Censorship Tests ({view_mode})")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Fatalities & Risks":
    st.subheader(f"Fatalities ({view_mode})")
    fig = px.bar(df_display, x="period", y="fatalities", color="country",
                 title=f"Fatalities Over Time ({view_mode})")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "Leaders & Losers":
    st.subheader("Global Leaders & Losers")
    leaders = df.groupby("country").agg({"takedown_requests":"sum"}).reset_index().sort_values("takedown_requests", ascending=False).head(5)
    losers = df.groupby("country").agg({"takedown_requests":"sum"}).reset_index().sort_values("takedown_requests", ascending=True).head(5)
    st.write("Top 5 Countries (Leaders)")
    st.dataframe(leaders)
    st.write("Bottom 5 Countries (Losers)")
    st.dataframe(losers)

elif choice == "Heatmap":
    st.subheader(f"Heatmap ({view_mode})")
    if view_mode == "Kenya":
        st.info("Kenya heatmap will show conflict events with lat/lon inside Kenya’s boundary.")
    else:
        st.info("Global heatmap will show conflict events worldwide.")
