"""
pages/4_Regional_Conflict_Map.py
County-level conflict events and fatalities across Kenya.
Choropleth map + bar rankings + event type breakdown.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(page_title="Regional Conflict · Observatory", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🗺️ Regional Conflict Map")
st.caption("County-level ACLED conflict events and fatalities across Kenya, Jun 2023 – Jun 2025")

with st.sidebar:
    st.markdown("### Filters")
    event_type_filter = st.multiselect(
        "Event type",
        ["Protests","Riots","Violence against civilians","Battles","Explosions/Remote violence"],
        default=["Protests","Riots","Violence against civilians"],
    )
    metric = st.radio("Map metric", ["Total events","Fatalities","Censorship trigger events"])
    year_range = st.select_slider("Year", options=[2023, 2024, 2025], value=(2023, 2025))

ev_sql = "', '".join(event_type_filter)

@st.cache_data(ttl=3600)
def load_regional(ev_sql, year_range):
    return run_query(f"""
        SELECT
            county,
            region,
            AVG(centroid_latitude)                          AS lat,
            AVG(centroid_longitude)                         AS lon,
            SUM(event_count)                                AS total_events,
            SUM(fatalities)                                 AS total_fatalities,
            COUNTIF(is_censorship_trigger_event)            AS trigger_events,
            COUNT(DISTINCT event_type)                      AS event_type_count,
            STRING_AGG(DISTINCT severity_level, ', ')       AS severity_levels
        FROM {table('fact_conflict_events')}
        WHERE event_type IN ('{ev_sql}')
          AND year BETWEEN {year_range[0]} AND {year_range[1]}
          AND county IS NOT NULL
        GROUP BY county, region
        ORDER BY total_events DESC
    """)

@st.cache_data(ttl=3600)
def load_event_type_breakdown():
    return run_query(f"""
        SELECT
            event_type,
            year,
            SUM(event_count)                    AS events,
            SUM(fatalities)                     AS fatalities
        FROM {table('fact_conflict_events')}
        GROUP BY event_type, year
        ORDER BY year, events DESC
    """)

@st.cache_data(ttl=3600)
def load_monthly_conflict():
    return run_query(f"""
        SELECT
            EXTRACT(YEAR FROM measurement_date)             AS year,
            EXTRACT(MONTH FROM measurement_date)            AS month,
            FORMAT('%04d-%02d',
                EXTRACT(YEAR FROM measurement_date),
                EXTRACT(MONTH FROM measurement_date))       AS year_month,
            SUM(event_count)                                AS events,
            SUM(fatalities)                                 AS fatalities,
            COUNTIF(is_censorship_trigger_event)            AS trigger_events
        FROM {table('fact_conflict_events')}
        GROUP BY year, month, year_month
        ORDER BY year_month
    """)

with st.spinner("Loading regional data…"):
    regional_df = load_regional(ev_sql, year_range)
    breakdown_df = load_event_type_breakdown()
    monthly_df = load_monthly_conflict()

# ── Map ───────────────────────────────────────────────────────────────────────
metric_col = {"Total events":"total_events","Fatalities":"total_fatalities","Censorship trigger events":"trigger_events"}[metric]

col_l, col_r = st.columns([2, 1])

with col_l:
    st.markdown(f"#### Kenya: {metric} by County")

    if regional_df.empty:
        st.warning("No data for selected filters.")
    else:
        fig_map = px.scatter_mapbox(
            regional_df.dropna(subset=["lat","lon"]),
            lat="lat", lon="lon",
            size=metric_col,
            color=metric_col,
            hover_name="county",
            hover_data={"lat":False,"lon":False,"region":True,
                        "total_events":True,"total_fatalities":True,"trigger_events":True},
            color_continuous_scale=["#16161A","#4A1B0C","#993C1D","#E8593C"],
            size_max=50,
            zoom=5.2,
            center={"lat": 0.0236, "lon": 37.9062},
            mapbox_style="carto-darkmatter",
            height=520,
        )
        fig_map.update_layout(
            paper_bgcolor="#0D0D0F",
            font_color="#E8E6DF",
            margin=dict(l=0,r=0,t=0,b=0),
            coloraxis_colorbar=dict(
                title=metric, tickfont=dict(color="#E8E6DF"),
                titlefont=dict(color="#E8E6DF"),
            ),
        )
        st.plotly_chart(fig_map, use_container_width=True)

with col_r:
    st.markdown("#### Top 10 Counties by Events")
    top10 = regional_df.head(10)
    fig_bar = px.bar(
        top10.sort_values("total_events"),
        x="total_events", y="county",
        orientation="h",
        color="total_fatalities",
        color_continuous_scale=["#16161A","#E8593C"],
        labels={"total_events":"Events","county":"","total_fatalities":"Fatalities"},
        height=480,
    )
    fig_bar.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", margin=dict(l=0,r=0,t=20,b=0),
        xaxis=dict(showgrid=False),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ── Event type breakdown ────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Event Type by Year")
    et_colors = {
        "Protests":                     PALETTE["teal"],
        "Riots":                        PALETTE["amber"],
        "Violence against civilians":   PALETTE["coral"],
        "Battles":                      PALETTE["purple"],
        "Explosions/Remote violence":   PALETTE["blue"],
    }
    fig_et = px.bar(
        breakdown_df, x="year", y="events",
        color="event_type", color_discrete_map=et_colors,
        barmode="group",
        labels={"events":"Events","year":"Year","event_type":"Type"},
        height=320,
    )
    fig_et.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", margin=dict(l=0,r=0,t=20,b=0),
        xaxis=dict(showgrid=False, type="category"),
        yaxis=dict(gridcolor="#2A2A2F"),
        legend=dict(orientation="h", y=1.05, font=dict(size=10)),
    )
    st.plotly_chart(fig_et, use_container_width=True)

with c2:
    st.markdown("#### Monthly Conflict Trend")
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Bar(
        x=monthly_df["year_month"], y=monthly_df["events"],
        name="Total events", marker_color=PALETTE["amber"], opacity=0.7,
    ))
    fig_mc.add_trace(go.Scatter(
        x=monthly_df["year_month"], y=monthly_df["trigger_events"],
        name="Protest/trigger events", line=dict(color=PALETTE["coral"], width=2),
        mode="lines+markers",
    ))
    fig_mc.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", height=320,
        margin=dict(l=0,r=0,t=20,b=0),
        xaxis=dict(showgrid=False, tickangle=45, tickfont=dict(size=8)),
        yaxis=dict(gridcolor="#2A2A2F"),
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig_mc, use_container_width=True)

st.divider()
st.dataframe(
    regional_df[["county","region","total_events","total_fatalities","trigger_events"]]
    .rename(columns={
        "county":"County","region":"Region",
        "total_events":"Events","total_fatalities":"Fatalities","trigger_events":"Protest Events",
    }),
    use_container_width=True, hide_index=True,
)
