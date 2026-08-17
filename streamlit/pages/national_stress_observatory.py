# pages/national_stress_observatory.py

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import (
    apply_layout,
    regime_color,
    confidence_color,
    correlation_color,
    inject_css,
)

from services.marts import (
    get_national_stress,
    get_regime_classification,
    get_ooni_weekly_signals,
)

from components.charts import add_threshold_lines
from components.kpis import metric_row
from components.status import render_state_badge, render_confidence_badge
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
    f"Country-level digital suppression pressure across {COUNTRY} "
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
        "Current Pressure",
        f"{latest['composite_pressure_score']:.2f}"
    ),
    (
        "Pressure Level",
        latest["pressure_level"]
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
        "protocol_stress_score (0-100, z-score-based), surfaced here as "
        "same-day corroboration. Not a term in Current Pressure -- "
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
This chart shows {COUNTRY}'s **observed national digital pressure**
-- `composite_pressure_score`, conflict (75%) and platform (25%),
per ADR-0004 -- and the documented pressure-level thresholds it is
banded against (ADR-0004).

**How to read this**

- **Coral / Orange line** → current observed pressure conditions
- **Dotted reference lines** → the SEVERE / ELEVATED / MODERATE
  thresholds `fact_country_pressure_daily` bands `pressure_level` on
""")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["composite_pressure_score"],
    name="Observed National Pressure",
    line=dict(
        color="#E8593C",
        width=3
    )
))

apply_layout(
    fig,
    "Observed National Pressure"
)

fig.update_layout(
    hovermode="x unified",
    yaxis_title="Pressure Score",
    xaxis_title="Date"
)

add_threshold_lines(
    fig,
    values=[2.0, 4.0, 6.5],
    labels=["MODERATE", "ELEVATED", "SEVERE"],
    opacity=[0.4, 0.5, 0.6],
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
This shows how many monitored protocols experienced elevated
interference conditions on each day.

Large spikes often indicate broader network-level stress rather
than isolated protocol instability.
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


# ============================================================
# ACLED PATH A REGIME CLASSIFICATION (ADR-0002 step (e))
# ============================================================

st.subheader("ACLED Regime Classification")

st.markdown("""
This section is a **separate, additive** view: it shows
`intelligence.acled_pressure_regimes` -- ACLED path A's weekly,
category-based classification -- alongside the continuous pressure
score above, not merged into it. Each week's regime, confidence, and
band assignment is repeated across the days of that week; a blank
week means no classification exists yet for that date (outside the
backfilled range).
""")

regime_df = get_regime_classification(
    st.session_state.start_date,
    st.session_state.end_date
)

if regime_df.empty or regime_df["regime_primary_regime"].isna().all():
    st.info(
        "No ACLED path A regime classification available for this date range."
    )
else:
    regime_valid = regime_df[regime_df["regime_primary_regime"].notna()]
    latest_regime = regime_valid.iloc[-1]

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        render_state_badge(
            "Current Regime",
            latest_regime["regime_primary_regime"],
            regime_color(latest_regime["regime_primary_regime"]),
        )

    with b2:
        render_confidence_badge(
            "Confidence",
            latest_regime["regime_confidence_level"],
            confidence_color(latest_regime["regime_confidence_level"]),
        )

    with b3:
        st.metric(
            "Transition Detected",
            "Yes" if latest_regime["regime_transition_detected"] else "No"
        )

    with b4:
        st.metric(
            "Transition Type",
            latest_regime["regime_transition_type"] or "—"
        )

    fig_regime = go.Figure()

    fig_regime.add_trace(go.Scatter(
        x=regime_valid["date_key"],
        y=regime_valid["regime_primary_regime"],
        mode="markers",
        marker=dict(
            size=8,
            color=[
                regime_color(r)
                for r in regime_valid["regime_primary_regime"]
            ]
        ),
        name="Primary Regime"
    ))

    apply_layout(
        fig_regime,
        "Weekly Regime Classification"
    )

    fig_regime.update_layout(
        yaxis_title="Regime",
        xaxis_title="Date"
    )

    st.plotly_chart(
        fig_regime,
        use_container_width=True
    )

    st.dataframe(
        regime_valid[
            [
                "date_key",
                "regime_primary_regime",
                "regime_confidence_level",
                "regime_transition_detected",
                "regime_transition_type",
                "regime_previous_regime",
                "regime_protest_band",
                "regime_violence_band",
                "regime_suppression_band",
                "regime_disorder_band",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # OONI WEEKLY SIGNAL vs ACLED REGIME (TD-97)
    # ========================================================

    st.subheader("OONI Weekly Signal vs. ACLED Regime")

    st.markdown("""
    Two independently-tracked OONI weekly series -- `anomalous_rate` (OONI's
    own ANOMALOUS verdict, `int.ooni_measurement_verdicts`) and
    `blocked_rate` (this pipeline's narrower BLOCKED classification,
    `int.ooni_experiment_results`) -- per protocol, at the same
    Saturday-anchored weekly grain as the regime classification above.
    Deliberately never merged into one score (ADR-0011): the two series can
    and do disagree, and are shown side by side rather than blended.
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

        # Regime bands: regime_valid is broadcast daily (one row per day,
        # repeating each week's classification) -- dedupe to one row per
        # Saturday-anchored week before drawing bands, or overlapping
        # semi-transparent vrects (up to 7 per week) would stack opacity
        # and render each week visibly darker than intended.
        regime_weekly = regime_valid.copy()
        regime_weekly["computed_week_start"] = regime_weekly["date_key"].apply(
            lambda d: pd.Timestamp(d) - pd.Timedelta(days=(pd.Timestamp(d).weekday() - 5) % 7)
        )
        regime_weekly = regime_weekly.drop_duplicates(
            subset="computed_week_start", keep="first"
        )

        for _, rrow in regime_weekly.iterrows():
            week_start = rrow["computed_week_start"]
            fig_weekly.add_vrect(
                x0=week_start,
                x1=week_start + pd.Timedelta(days=7),
                fillcolor=regime_color(rrow["regime_primary_regime"]),
                opacity=0.15,
                line_width=0,
                layer="below",
            )

        apply_layout(
            fig_weekly,
            f"{weekly_protocol}: OONI Weekly Signal vs. ACLED Regime"
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

        badge_col, _ = st.columns([1, 3])

        with badge_col:
            render_state_badge(
                "Tested lag-correlation vs. ACLED regime (historical, all-time)",
                "WEAK_OR_NO_RELATIONSHIP",
                correlation_color("WEAK_OR_NO_RELATIONSHIP"),
            )

        st.markdown("""
        **How to read this alongside the regime chart above:** the two
        series here move at their own weekly grain and are shown against
        the same Saturday-anchored regime bands as the chart above -- but
        visible movement in a series is not the same claim as a *tested*
        statistical relationship. Lag-correlation between these exact two
        series and ACLED's regime severity has been computed and tested at
        every lag from -2 to +2 weeks
        (`intelligence.ooni_acled_lag_correlation`, ADR-0011). The honest
        result, system-wide across all history, is weak or absent almost
        everywhere -- the one exception ever found (a single
        `MODERATE_RELATIONSHIP` week) was traced to a data-quality artifact
        and resolved (TD-93), and no `STRONG_RELATIONSHIP` week has ever
        occurred. This chart does not re-test that finding live; see
        **Methodology & Statistical Guardrails** for the full historical
        disclosure.
        """)

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
            "pressure_level",
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
