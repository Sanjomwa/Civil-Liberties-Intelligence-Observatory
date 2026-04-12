"""
pages/5_Content_Removal.py
Google Transparency + Lumen takedown analysis.
Who requests removal, what reasons, which platforms, and trends over time.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.bq_client import run_query, table, PALETTE

st.set_page_config(page_title="Content Removal · Observatory", page_icon="📋", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📋 Content Removal & Takedowns")
st.caption("Google Transparency Report + Lumen takedown notices targeting Kenya, Jun 2023 – Jun 2025")

with st.sidebar:
    st.markdown("### Filters")
    sources = st.multiselect(
        "Source",
        ["google_requests","google_detailed","lumen"],
        default=["google_requests","google_detailed","lumen"],
        format_func=lambda x: {"google_requests":"Google Requests","google_detailed":"Google Detailed","lumen":"Lumen"}[x],
    )

src_sql = "', '".join(sources)

@st.cache_data(ttl=3600)
def load_summary(src_sql):
    return run_query(f"""
        SELECT
            source,
            COUNT(*)                            AS records,
            SUM(number_of_requests)             AS total_requests,
            SUM(items_requested_removal)        AS items_targeted,
            COUNT(DISTINCT platform)            AS platforms,
            COUNT(DISTINCT requestor_name)      AS requestors
        FROM {table('fact_takedown_requests')}
        WHERE source IN ('{src_sql}')
        GROUP BY source
    """)

@st.cache_data(ttl=3600)
def load_by_reason(src_sql):
    return run_query(f"""
        SELECT
            reason,
            source,
            SUM(number_of_requests)             AS requests,
            SUM(items_requested_removal)        AS items_targeted
        FROM {table('fact_takedown_requests')}
        WHERE source IN ('{src_sql}')
          AND reason IS NOT NULL
        GROUP BY reason, source
        ORDER BY requests DESC
        LIMIT 25
    """)

@st.cache_data(ttl=3600)
def load_trends(src_sql):
    return run_query(f"""
        SELECT
            year_month,
            source,
            reason_group,
            total_requests,
            total_items_targeted,
            cumulative_requests
        FROM {table('fact_takedown_trends')}
        WHERE source IN ('{src_sql}')
        ORDER BY year_month, source
    """)

@st.cache_data(ttl=3600)
def load_requestors(src_sql):
    return run_query(f"""
        SELECT
            r.requestor_name,
            r.requestor_type,
            r.source,
            SUM(t.number_of_requests)           AS total_requests
        FROM {table('fact_takedown_requests')} t
        JOIN {table('dim_requestors')} r
          ON t.requestor_name = r.requestor_name
         AND t.source = r.source
        WHERE t.source IN ('{src_sql}')
        GROUP BY r.requestor_name, r.requestor_type, r.source
        ORDER BY total_requests DESC
        LIMIT 20
    """)

@st.cache_data(ttl=3600)
def load_reason_platform_heatmap(src_sql):
    return run_query(f"""
        SELECT
            reason,
            platform,
            SUM(number_of_requests)             AS requests
        FROM {table('fact_takedown_requests')}
        WHERE source IN ('{src_sql}')
          AND reason IS NOT NULL
          AND platform IS NOT NULL
        GROUP BY reason, platform
        HAVING SUM(number_of_requests) > 0
        ORDER BY requests DESC
    """)

with st.spinner("Loading takedown data…"):
    summary_df  = load_summary(src_sql)
    reason_df   = load_by_reason(src_sql)
    trends_df   = load_trends(src_sql)
    req_df      = load_requestors(src_sql)
    heat_df     = load_reason_platform_heatmap(src_sql)

# ── KPI row ──────────────────────────────────────────────────────────────────
cols = st.columns(len(summary_df) if not summary_df.empty else 1)
for i, (_, row) in enumerate(summary_df.iterrows()):
    label = {"google_requests":"Google Requests","google_detailed":"Google Detailed","lumen":"Lumen"}.get(row.source, row.source)
    with cols[i]:
        st.metric(f"{label} — total requests", f"{int(row.total_requests or 0):,}")

st.divider()

# ── Takedown trend ────────────────────────────────────────────────────────────
st.markdown("#### Monthly Takedown Request Volume")

source_colors = {
    "google_requests":  PALETTE["teal"],
    "google_detailed":  PALETTE["blue"],
    "lumen":            PALETTE["amber"],
}
trends_agg = trends_df.groupby(["year_month","source"])["total_requests"].sum().reset_index()

fig_trend = px.line(
    trends_agg, x="year_month", y="total_requests",
    color="source", color_discrete_map=source_colors,
    markers=True,
    labels={"year_month":"","total_requests":"Requests","source":"Source"},
    height=300,
)
fig_trend.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF", margin=dict(l=0,r=0,t=20,b=0),
    xaxis=dict(showgrid=False, tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(gridcolor="#2A2A2F"),
    legend=dict(orientation="h", y=1.08),
)
st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ── Reason × platform heatmap ────────────────────────────────────────────────
st.markdown("#### Reason × Platform Heatmap")
st.caption("Which platforms receive the most removal requests and for what reasons?")

top_reasons   = heat_df.groupby("reason")["requests"].sum().nlargest(12).index.tolist()
top_platforms = heat_df.groupby("platform")["requests"].sum().nlargest(10).index.tolist()
h_filt = heat_df[heat_df["reason"].isin(top_reasons) & heat_df["platform"].isin(top_platforms)]
pivot  = h_filt.pivot(index="reason", columns="platform", values="requests").fillna(0)

fig_heat = go.Figure(go.Heatmap(
    z=np.log1p(pivot.values),
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    customdata=pivot.values,
    hovertemplate="Reason: %{y}<br>Platform: %{x}<br>Requests: %{customdata:,}<extra></extra>",
    colorscale=[[0,"#16161A"],[0.4,"#0C447C"],[0.7,"#185FA5"],[1.0,"#E8593C"]],
    showscale=True,
    colorbar=dict(title="log(requests)", tickfont=dict(color="#E8E6DF"), titlefont=dict(color="#E8E6DF")),
    text=[[f"{int(v):,}" if v > 0 else "" for v in row] for row in pivot.values],
    texttemplate="%{text}", textfont=dict(size=9),
))
fig_heat.update_layout(
    plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    height=420,
    margin=dict(l=220, r=20, t=20, b=120),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Top reasons + top requestors ─────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Top Removal Reasons")
    reason_agg = reason_df.groupby("reason")["requests"].sum().sort_values().tail(15)
    fig_r = px.bar(
        reason_agg.reset_index(), x="requests", y="reason",
        orientation="h",
        color="requests",
        color_continuous_scale=["#16161A","#E8593C"],
        labels={"requests":"Requests","reason":""},
        height=380,
    )
    fig_r.update_layout(
        plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
        font_color="#E8E6DF", margin=dict(l=0,r=0,t=0,b=0),
        xaxis=dict(showgrid=False),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_r, use_container_width=True)

with c2:
    st.markdown("#### Top Requestors")
    if not req_df.empty:
        req_colors = {
            "Government / Law Enforcement": PALETTE["coral"],
            "Rights Holder / Media":        PALETTE["amber"],
            "Legal Entity":                 PALETTE["blue"],
            "Private / Commercial":         PALETTE["teal"],
        }
        fig_req = px.bar(
            req_df.head(15).sort_values("total_requests"),
            x="total_requests", y="requestor_name",
            color="requestor_type",
            color_discrete_map=req_colors,
            orientation="h",
            labels={"total_requests":"Requests","requestor_name":"","requestor_type":"Type"},
            height=380,
        )
        fig_req.update_layout(
            plot_bgcolor="#0D0D0F", paper_bgcolor="#0D0D0F",
            font_color="#E8E6DF", margin=dict(l=0,r=0,t=0,b=0),
            xaxis=dict(showgrid=False),
            legend=dict(orientation="h", y=1.05, font=dict(size=10)),
        )
        st.plotly_chart(fig_req, use_container_width=True)
    else:
        st.info("Requestor data not available for selected sources.")
