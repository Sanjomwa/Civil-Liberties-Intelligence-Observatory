import pandas as pd
import plotly.express as px
import streamlit as st

from core.state import init_state
from core.config import COUNTRY
from core.constants import REGIME_STATES
from core.filters import render_sidebar
from core.theme import apply_layout, stress_color, regime_color, inject_css
from services.marts import (
    get_conflict_drivers,
    get_ooni_corroboration,
    get_platform_drivers,
    get_pressure_attribution_daily,
)
from components.status import render_state_badge
from components.trust import render_trust_strip, attribution_footer


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Pressure Attribution",
    page_icon="🧾",
    layout="wide"
)

inject_css()


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# DATA
# ============================================================

df = get_pressure_attribution_daily(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No pressure-attribution data available for this window.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("🧾 Pressure Attribution")

st.caption(f"""
Decomposes {COUNTRY}'s composite pressure score into its named,
sourced drivers for any date — an attributed, citable answer to
"why is pressure at this level right now, specifically."

The composite has exactly two arithmetic inputs (ADR-0004 weights):
ACLED conflict intensity (75%, weekly grain) and Google Transparency
platform pressure (25%, semiannual grain). OONI network measurement
is shown as independent same-day corroboration — it does not feed
the composite arithmetically. Legal (Lumen) is benched (ADR-0004)
and carries zero weight.
""")

render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# DATE SELECTION
# ============================================================

available_dates = sorted(df["measurement_date"].unique(), reverse=True)

selected_date = st.selectbox(
    "Attribution date",
    available_dates,
    format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d"),
)

row = df[df["measurement_date"] == selected_date].iloc[0]
date_str = pd.Timestamp(selected_date).strftime("%Y-%m-%d")
week_start = pd.Timestamp(row["conflict_week_start_date"]).date()


# ============================================================
# HEADLINE KPIs
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Composite Pressure",
    f"{row['composite_pressure_score']:.2f}",
    delta=(
        f"{row['composite_delta_7d']:+.2f} vs prior week"
        if pd.notna(row["composite_delta_7d"]) else None
    ),
    delta_color="inverse",
)

with c2:
    render_state_badge(
        "Pressure Level",
        row["pressure_level"],
        stress_color(row["pressure_level"]),
    )

c3.metric(
    "Conflict Share",
    f"{row['conflict_share'] * 100:.1f}%"
    if pd.notna(row["conflict_share"]) else "—",
)

regime = row["regime_primary_regime"]

with c4:
    render_state_badge(
        "Regime (ACLED Path A)",
        regime if pd.notna(regime) else "No classification",
        regime_color(regime),
    )

if pd.notna(regime) and regime in REGIME_STATES:
    st.markdown(
        f"Regime engine classifies the week of **{week_start}** as "
        f"<span style='color:{REGIME_STATES[regime]}'><b>{regime}</b></span> "
        f"(confidence: {row['regime_confidence_level']})"
        + (
            f" — transition: {row['regime_transition_type']}"
            if pd.notna(row.get("regime_transition_type"))
            and bool(row.get("regime_transition_detected"))
            else ""
        ),
        unsafe_allow_html=True,
    )

st.divider()


# ============================================================
# ARITHMETIC DECOMPOSITION
# ============================================================

st.subheader("What the score is made of")

terms = pd.DataFrame([
    {
        "term": "Conflict (ACLED)",
        "source_score": row["conflict_pressure_score"],
        "weight": row["conflict_weight"],
        "contribution": row["conflict_contribution"],
        "share": row["conflict_share"],
        "grain": "Weekly aggregate, broadcast across the week",
    },
    {
        "term": "Platform (Google Transparency)",
        "source_score": row["platform_pressure_score"],
        "weight": row["platform_weight"],
        "contribution": row["platform_contribution"],
        "share": row["platform_share"],
        "grain": "Semiannual period, broadcast across ~6 months",
    },
])

fig = px.bar(
    terms,
    x="contribution",
    y="term",
    orientation="h",
    color="term",
    text=terms["share"].map(
        lambda s: f"{s * 100:.1f}%" if pd.notna(s) else "—"
    ),
)
fig.update_layout(showlegend=False)
apply_layout(fig, f"Composite {row['composite_pressure_score']:.2f} = contributions, {date_str}")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    terms.rename(columns={
        "term": "Term",
        "source_score": "Source score",
        "weight": "Weight",
        "contribution": "Contribution",
        "share": "Share of composite",
        "grain": "Real temporal grain",
    }),
    use_container_width=True,
    hide_index=True,
)

if pd.notna(row["composite_delta_7d"]):
    conflict_d = row["conflict_contribution_delta_7d"]
    platform_d = row["platform_contribution_delta_7d"]
    st.markdown(
        f"**Week-over-week movement:** composite "
        f"{row['composite_delta_7d']:+.2f} = conflict {conflict_d:+.2f} "
        f"+ platform {platform_d:+.2f}. "
        + (
            "All movement this week is conflict-term movement — the "
            "platform term only steps at half-year reporting boundaries."
            if pd.notna(platform_d) and abs(platform_d) < 0.005
            else "The platform term stepped at a half-year reporting boundary this week."
        )
    )

st.caption(
    "Grain honesty: the composite is a weekly step function — the conflict "
    "term is constant within each Saturday-anchored ACLED week, and the "
    "platform term is constant within each semiannual Google reporting "
    "period. Day-to-day movement within a week is zero by construction. "
    "Legal (Lumen) pressure is benched per ADR-0004 and contributes 0."
)

st.divider()


# ============================================================
# CONFLICT DRIVERS (weekly grain)
# ============================================================

st.subheader(f"Conflict drivers — ACLED week of {week_start}")

conflict_df = get_conflict_drivers(week_start)

if conflict_df.empty:
    st.info("No classified ACLED rows for this week.")
else:
    wk = conflict_df.iloc[0]
    st.markdown(
        f"This week's conflict input: **{int(wk['week_conflict_events'])} "
        f"events**, **{int(wk['week_fatalities'])} fatalities** across "
        f"{conflict_df['admin1'].nunique()} counties. Each row below is a "
        f"classified ACLED weekly-aggregate record; its share is of the "
        f"week's pre-log intensity mass (events + 3×fatalities), not of "
        f"the log-scale score."
    )

    top = conflict_df.head(15).copy()
    top["driver"] = (
        top["sub_event_type"] + " — " + top["admin1"]
    )

    fig2 = px.bar(
        top.sort_values("weekly_intensity_share"),
        x="weekly_intensity_share",
        y="driver",
        orientation="h",
        color="pressure_domain",
        hover_data=["event_type", "events", "fatalities",
                    "severity_tier", "classification_confidence"],
    )
    apply_layout(fig2, "Top drivers by share of weekly conflict intensity mass")
    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(
        top[[
            "weekly_intensity_rank", "event_type", "sub_event_type",
            "admin1", "events", "fatalities", "weekly_intensity_share",
            "pressure_domain", "is_suppression_marker", "severity_tier",
            "classification_confidence", "methodology_risk_level",
        ]].rename(columns={
            "weekly_intensity_rank": "#",
            "event_type": "ACLED event type",
            "sub_event_type": "Sub-event type",
            "admin1": "County",
            "events": "Events",
            "fatalities": "Fatalities",
            "weekly_intensity_share": "Intensity share",
            "pressure_domain": "Pressure domain",
            "is_suppression_marker": "Suppression marker",
            "severity_tier": "Severity",
            "classification_confidence": "Classification confidence",
            "methodology_risk_level": "Methodology risk",
        }),
        use_container_width=True,
        hide_index=True,
    )

    notes = conflict_df[conflict_df["classification_note"].notna()]
    if not notes.empty:
        with st.expander("Classification notes for this week's rows"):
            for _, n in notes.head(10).iterrows():
                st.markdown(
                    f"- **{n['sub_event_type']} — {n['admin1']}**: "
                    f"{n['classification_note']}"
                )

    st.caption(
        "ACLED grain: weekly aggregates anchored to Saturday. Nothing in "
        "this data distinguishes which day within the week an event "
        "occurred (minimum detectable lag: 7 days). classification_"
        "confidence and methodology_risk_level are KCLIO's own per-row "
        "qualifiers (int.acled_event_classification, ACLED_INTELLIGENCE_"
        "FRAMEWORK_V1)."
    )

st.divider()


# ============================================================
# PLATFORM DRIVERS (semiannual grain)
# ============================================================

period_start = row["platform_period_start"]
period_end = row["platform_period_end"]

period_label = (
    f"{pd.Timestamp(period_start).date()} → "
    + (f"{pd.Timestamp(period_end).date()}" if pd.notna(period_end) else "present")
    if pd.notna(period_start) else "no period on record"
)

st.subheader(f"Platform drivers — Google Transparency period {period_label}")

if pd.isna(period_start):
    st.info("No Google Transparency period covers this date.")
else:
    platform_df = get_platform_drivers(pd.Timestamp(period_start).date())

    if platform_df.empty:
        st.info(
            "No product/reason detail exists for this period — only "
            f"request-side totals (requests: {int(row['google_requests'])}, "
            f"detailed total: {int(row['detailed_total'])})."
        )
    else:
        p = platform_df.iloc[0]
        st.markdown(
            f"Period totals: **{int(p['google_requests']) if pd.notna(p['google_requests']) else '—'} "
            f"government removal requests**; detailed items by product/reason: "
            f"**{int(p['period_detailed_total'])}**. Requests have no "
            f"product/reason breakdown in the source — only the detailed "
            f"items decompose below."
        )

        fig3 = px.bar(
            platform_df.assign(
                driver=platform_df["product"] + " — " + platform_df["reason"]
            ).sort_values("period_detailed_share"),
            x="period_detailed_share",
            y="driver",
            orientation="h",
        )
        apply_layout(fig3, "Removal items by product and cited reason (share of period)")
        st.plotly_chart(fig3, use_container_width=True)

    st.warning(
        "Grain limit, stated plainly: Google publishes this data "
        "semiannually. This evidence contextualizes the ~6-month period "
        "containing the selected date; it cannot explain any specific "
        "day's or week's movement. Within this period, 100% of composite "
        "movement is conflict-term movement."
    )

st.divider()


# ============================================================
# OONI CORROBORATION (daily grain — NOT a composite input)
# ============================================================

st.subheader(f"OONI network measurement, {date_str} — independent corroboration")

st.markdown(
    "OONI probes measured the following on this exact date, per app and "
    "protocol layer. **This evidence does not feed the composite score** "
    "— it is independent, same-day network measurement that corroborates "
    "(or fails to corroborate) pressure readings derived from conflict "
    "and platform sources."
)

ooni_df = get_ooni_corroboration(pd.Timestamp(selected_date).date())

if ooni_df.empty:
    st.info(
        "No OONI measurements on this date (OONI coverage: Jun 2023 – "
        "Jun 2025)."
    )
else:
    signals = ooni_df[ooni_df["blocking_signal_count"] > 0]

    if signals.empty:
        st.success(
            f"No blocking signals in {int(ooni_df['total_experiment_results'].sum()):,} "
            f"experiment results across {ooni_df['test_name'].nunique()} tests — "
            "OONI does not corroborate network-layer interference on this date."
        )
    else:
        top_sig = signals.iloc[0]
        st.markdown(
            f"**{int(signals['blocking_signal_count'].sum())} blocking "
            f"signals** recorded. Strongest: **{top_sig['test_name']}** on "
            f"the **{top_sig['protocol'].upper()}** layer — "
            f"{int(top_sig['blocking_signal_count'])} signals in "
            f"{int(top_sig['total_experiment_results'])} results "
            f"({top_sig['blocking_signal_rate'] * 100:.1f}% of that test's "
            f"own measurements; {int(top_sig['high_confidence_events'])} "
            f"high-confidence)."
        )

    st.dataframe(
        ooni_df[[
            "test_name", "protocol", "total_experiment_results",
            "blocking_signal_count", "blocked_results",
            "high_confidence_events", "medium_confidence_events",
            "blocking_signal_rate",
        ]].rename(columns={
            "test_name": "Test (app)",
            "protocol": "Protocol",
            "total_experiment_results": "Results",
            "blocking_signal_count": "Blocking signals",
            "blocked_results": "BLOCKED",
            "high_confidence_events": "High conf.",
            "medium_confidence_events": "Medium conf.",
            "blocking_signal_rate": "Own-test rate",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Rates are per-test only and never pooled across tests "
        "(TD-49/TD-54): dnscheck's high-volume, structurally zero-signal "
        "rows (TD-55) stay in their own row and cannot dilute app-specific "
        "rates. Confidence bands per marts.dim_censorship_confidence "
        "(ADR-0001)."
    )

st.divider()

# TD-63: this page also surfaces Google Transparency Report-derived
# platform-driver numbers above; that source's attribution is a separate,
# unresolved question (TD-64, license status "Cannot Determine") and is
# deliberately not claimed here alongside ACLED/OONI.
attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
