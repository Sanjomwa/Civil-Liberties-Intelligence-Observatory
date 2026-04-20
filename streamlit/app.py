# streamlit/app.py

import streamlit as st
from utils.bq_client import run_query, table

st.set_page_config(
    page_title="Kenya Civil Liberties Observatory",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Kenya Civil Liberties & Censorship Observatory")
st.caption("Analyzing the relationship between political unrest and digital censorship (2023–2025)")

# ─────────────────────────────────────────────────────────────
# GLOBAL FILTER HELPERS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_date_bounds():
    df = run_query(f"""
        SELECT
            MIN(measurement_date) AS min_date,
            MAX(measurement_date) AS max_date
        FROM {table('civil_liberties_mart')}
    """)
    return df.iloc[0]["min_date"], df.iloc[0]["max_date"]


@st.cache_data(ttl=3600)
def get_platforms():
    df = run_query(f"""
        SELECT DISTINCT platform
        FROM {table('platform_censorship_mart')}
        ORDER BY platform
    """)
    return df["platform"].tolist()


# ─────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────

st.sidebar.header("🔍 Global Filters")

min_date, max_date = get_date_bounds()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

platforms = get_platforms()

selected_platforms = st.sidebar.multiselect(
    "Platforms",
    options=platforms,
    default=[]
)

# Store globally
st.session_state["start_date"] = str(date_range[0])
st.session_state["end_date"] = str(date_range[1])
st.session_state["platforms"] = selected_platforms

# ─────────────────────────────────────────────────────────────
# LANDING CONTENT
# ─────────────────────────────────────────────────────────────

st.markdown("## 📊 What This Dashboard Answers")

st.markdown("""
**Core Question:**

> How does political unrest correlate with digital censorship in Kenya?

### Navigate using the sidebar:

- **Censorship Timeline** → Trends over time  
- **Platform Blocking** → Which platforms are targeted  
- **Protest vs Censorship** → Correlation analysis  
- **Suppression Windows** → Patterns of repression  
- **Finance Bill Crisis** → Case study  

### Notes:
- All metrics are precomputed in BigQuery marts
- Data is filtered globally using the sidebar
- No raw datasets are used
""")
