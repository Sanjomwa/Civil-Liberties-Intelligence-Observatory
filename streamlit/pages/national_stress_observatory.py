# pages/national_stress_observatory.py

import streamlit as st
import plotly.graph_objects as go

from core.config import COUNTRY
from core.constants import LABELS_HIDDEN_NOTE
from core.state import init_state
from core.filters import render_sidebar
from core.theme import (
    apply_layout,
    inject_css,
)

from services.marts import (
    get_national_stress,
    get_ooni_weekly_signals,
)

from components.kpis import metric_row
from components.trust import (
    render_trust_strip,
    attribution_footer
)


# ============================================================
# PAGE CONFIG
# ============================================================

inject_css()


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# DATA
# ============================================================

df = get_national_stress(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No national stress data available.")
    st.stop()


latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("National Stress Observatory")

st.caption(
    f"Country-level composite pressure index (experimental) for {COUNTRY} "
    "(data currently covers June 2023 – June 2025)"
)


# ============================================================
# TRUST STRIP
# ============================================================

render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["date_key"].max()
)

st.divider()


# ============================================================
# KPI ROW
# ============================================================

metric_row([
    (
        "Composite index (experimental; not validated), latest date",
        f"{latest['composite_pressure_score']:.2f}"
    ),
    (
        "Elevated Protocols",
        f"{int(latest['elevated_protocol_count'])}"
    ),
    (
        "Sample Quality",
        f"{latest['avg_sample_quality_score']:.2f}"
    ),
])

st.metric(
    "OONI Protocol-Stress Signal (independent, not included in composite)",
    f"{latest['max_protocol_stress_score']:.1f}",
    help=(
        "intelligence.protocol_signal_regimes' statistically-qualified "
        "protocol_stress_score (0-100, z-score-based), shown here alongside "
        "the composite as a separate measurement. Not a term in the "
        "composite index -- "
        "composite_pressure_score is conflict (75%) and platform (25%) "
        "only, per ADR-0004/ADR-0006."
    )
)

st.divider()


# ============================================================
# NATIONAL PRESSURE TIMELINE
# ============================================================

st.subheader("National Digital Pressure Trend")

st.markdown(f"""
This chart shows {COUNTRY}'s **composite pressure index (experimental)**
-- `composite_pressure_score`, conflict (75%) and platform (25%),
per ADR-0004. The line is the index value on each date; it is an
experimental number, not a validated measure.
""")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["composite_pressure_score"],
    name="Composite index (experimental; not validated)",
    line=dict(
        color="#E8593C",
        width=3
    )
))

apply_layout(
    fig,
    "Composite index (experimental; not validated)"
)

fig.update_layout(
    hovermode="x unified",
    yaxis_title="Composite index",
    xaxis_title="Date"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()


# ============================================================
# PROTOCOL ESCALATION LOAD
# ============================================================

st.subheader("Protocol Escalation Load")

st.markdown("""
This shows how many monitored protocols had OONI measurements classed
as anomalous against their own baseline on each day.

A day when several protocols are elevated at once is a measurement
pattern, not evidence of what caused it; it can reflect network
conditions, measurement coverage, or changes at the services tested.
""")

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["elevated_protocol_count"],
    fill="tozeroy",
    line=dict(
        color="#EF9F27",
        width=2
    ),
    name="Elevated Protocol Count"
))

apply_layout(
    fig3,
    "Elevated Protocol Load"
)

fig3.update_layout(
    yaxis_title="Protocol Count",
    xaxis_title="Date"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

st.divider()


# Item 34 (2026-11-16): the ACLED path A regime display (latest-week regime
# and confidence badges, transition metrics, weekly regime scatter, regime
# table with per-family bands, the regime-coloured vrects behind the OONI
# weekly chart, and the lag-correlation-vs-regime badge and text) was
# removed from public view until the labels are validated against a
# pre-specified list of events. get_regime_classification() in
# services/marts.py is kept, unused.

st.info(LABELS_HIDDEN_NOTE)


# ============================================================
# OONI WEEKLY SIGNAL (TD-97)
# ============================================================

st.subheader("OONI Weekly Signal")

st.markdown("""
Two independently-tracked OONI weekly series -- `anomalous_rate` (OONI's
own ANOMALOUS verdict, `int.ooni_measurement_verdicts`) and
`blocked_rate` (this pipeline's narrower BLOCKED classification,
`int.ooni_experiment_results`) -- per protocol, at a Saturday-anchored
weekly grain. Deliberately never merged into one score (ADR-0011): the
two series can and do disagree, and are shown side by side rather than
blended.
""")

weekly_df = get_ooni_weekly_signals(
    st.session_state.start_date,
    st.session_state.end_date
)

if weekly_df.empty:
    st.info(
        "No OONI weekly signal data available for this date range."
    )
else:
    weekly_protocol = st.selectbox(
        "Select protocol (test) for the weekly signal chart",
        sorted(weekly_df["test_name"].dropna().unique()),
        key="weekly_signal_protocol",
    )

    wp_df = weekly_df[
        weekly_df["test_name"] == weekly_protocol
    ].sort_values("week_start_date")

    fig_weekly = go.Figure()

    fig_weekly.add_trace(go.Scatter(
        x=wp_df["week_start_date"],
        y=wp_df["anomalous_rate"],
        name="Anomalous rate (OONI verdict)",
        line=dict(color="#5B8DEF", width=2),
    ))

    fig_weekly.add_trace(go.Scatter(
        x=wp_df["week_start_date"],
        y=wp_df["blocked_rate"],
        name="Blocked rate (BLOCKED classification)",
        line=dict(color="#E8593C", width=2, dash="dash"),
    ))

    apply_layout(
        fig_weekly,
        f"{weekly_protocol}: OONI Weekly Signal"
    )

    fig_weekly.update_layout(
        yaxis_title="Rate",
        xaxis_title="Week starting"
    )

    st.plotly_chart(
        fig_weekly,
        use_container_width=True
    )

    _n_weeks = len(wp_df)
    _sparse_weeks = int(
        (
            wp_df["anomalous_sparse_baseline_flag"].fillna(False)
            | wp_df["blocked_sparse_baseline_flag"].fillna(False)
            | wp_df["anomalous_low_sample_flag"].fillna(False)
            | wp_df["blocked_low_sample_flag"].fillna(False)
        ).sum()
    )

    st.caption(
        f"Of {_n_weeks} weeks shown for {weekly_protocol}, {_sparse_weeks} "
        "are flagged sparse-baseline or low-sample on at least one series "
        "(`*_sparse_baseline_flag`/`*_low_sample_flag`, "
        "features.ooni_weekly_signals) -- shown as-is, not hidden or "
        "smoothed over."
    )

st.divider()


# ============================================================
# RAW TABLE
# ============================================================

st.subheader("Observatory Data")

st.dataframe(
    df[
        [
            "date_key",
            "composite_pressure_score",
            "max_protocol_stress_score",
            "elevated_protocol_count",
            "avg_sample_quality_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
