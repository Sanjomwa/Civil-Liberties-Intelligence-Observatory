import streamlit as st
import pandas as pd

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import inject_css
from components.trust import attribution_footer
from services.marts import get_correlation_history_summary


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
# HEADER
# ============================================================

st.title("🧠 Methodology & Statistical Guardrails")

st.caption(f"""
Formal statistical controls, anomaly logic, confidence weighting,
and inference protections used across {COUNTRY}'s Digital Repression
Observability System.

This page explains **how every signal is validated before entering
intelligence outputs.**
""")

st.divider()


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

st.subheader("System Architecture")

st.markdown("""
The observability stack is composed of four analytical layers:

**1. Raw Measurement Ingestion**

- OONI network measurements
- protocol observations
- platform accessibility signals

**2. Feature Engineering**

Transforms raw measurements into:

- anomaly scores
- rolling baselines
- weighted interference indicators
- protocol reliability metrics

**3. Intelligence Inference**

Applies:

- regime classification
- protocol relationship modeling
- lag dependency inference
- confidence scoring

**4. Reporting Layer**

Produces operational dashboards for:

- national suppression pressure
- protocol stress intelligence
- ASN behavioral attribution
- incident reconstruction
""")

st.divider()


# ============================================================
# ROLLING BASELINE MODEL
# ============================================================

st.subheader("Rolling Baseline Windows")

st.markdown("""
Each protocol is evaluated against its own rolling 30-day trailing average
of `signal_rate` (`baseline_signal_rate_30d`, computed in
`features/protocol_daily_signals.sql`) -- a plain unweighted mean. There is
no decay or weighting term applied to older vs. more recent days anywhere in
this calculation.

This prevents:

- false alerts from isolated spikes
- static threshold bias
""")

st.divider()


# ============================================================
# CONFIDENCE WEIGHTING
# ============================================================

st.subheader("Confidence Weighting Logic")

st.markdown("""
Confidence weighting is not a fixed three-tier lookup table. The weight
actually applied in correlation scoring is continuous, computed per
protocol-day in `intelligence/protocol_relationships.sql`:

`final_confidence_score = LEAST(1.0, 0.60 x sample_quality_score + 0.40 x
strongest_relationship_confidence_score)`

The displayed `rolling_pressure_corr` is this value multiplied through the
full chain: the raw rolling `CORR()` between protocol anomaly and national
pressure, x `sample_quality_score`, x `final_confidence_score` -- or, on the
protocol-days where no `protocol_relationships` row exists to join at all
(not merely a low relationship-confidence score, which the formula above
already handles via `COALESCE(..., 0.0)`), a fixed 0.25 fallback in place of
`final_confidence_score` (`protocol_repression_correlation_mart.sql`). This
chain is why the displayed correlation sits well below the raw statistical
correlation -- see "Correlation Strength: Historical Track Record" below.

Low-confidence observations are mathematically suppressed before correlation
scoring by the same multiplication -- this prevents sparse evidence from
amplifying synthetic suppression signatures.
""")

st.divider()


# ============================================================
# VARIANCE GUARDRAILS
# ============================================================

st.subheader("Variance Protection Rules")

rules = pd.DataFrame({
    "Guardrail": [
        "Minimum rolling observations",
        "Zero variance rejection",
        "Sparse baseline rejection",
        "Low sample suppression"
    ],
    "Threshold": [
        "18+ observations",
        "stddev > 0",
        "7+ baseline days (min_baseline_days_30d, protocol_daily_signals.sql)",
        "5+ measurements/day (min_measurements_per_day, protocol_daily_signals.sql)"
    ]
})

st.dataframe(
    rules,
    use_container_width=True,
    hide_index=True
)

st.markdown("""
Correlation is only computed when statistical validity exists.

Otherwise the system explicitly labels windows as:

- INSUFFICIENT_HISTORY
- ZERO_VARIANCE_WINDOW
- INSUFFICIENT_DATA
""")

st.divider()


# ============================================================
# REGIME CLASSIFICATION
# ============================================================

st.subheader("Protocol Regime Classification")

regimes = pd.DataFrame({
    "Regime": [
        "NORMAL_RANGE",
        "ELEVATED",
        "SEVERE_ELEVATION",
        "INSUFFICIENT_DATA",
        "BELOW_BASELINE"
    ],
    "Meaning": [
        "Normal protocol behavior",
        "Moderate anomaly escalation",
        "Strong suppression anomaly",
        "Evidence too sparse",
        "Suppressed anomaly activity"
    ]
})

st.dataframe(
    regimes,
    use_container_width=True,
    hide_index=True
)

st.divider()


# ============================================================
# ALIGNMENT STATES
# ============================================================

st.subheader("Correlation Alignment States")

alignment = pd.DataFrame({
    "State": [
        "SYNCHRONIZED_ESCALATION",
        "PROTOCOL_DIVERGENCE",
        "PRESSURE_ONLY",
        "INVERSE_MOVEMENT",
        "NO_CLEAR_ALIGNMENT"
    ],
    "Interpretation": [
        "Protocol and national pressure rise together",
        "Protocol anomaly without national escalation",
        "Pressure rise without protocol anomaly",
        "Protocol moves opposite pressure",
        "No statistically meaningful relation"
    ]
})

st.dataframe(
    alignment,
    use_container_width=True,
    hide_index=True
)

st.divider()


# ============================================================
# CORRELATION STRENGTH: HISTORICAL TRACK RECORD
# ============================================================

st.subheader("Correlation Strength: Historical Track Record")

try:
    _corr_summary = get_correlation_history_summary()
except Exception:
    _corr_summary = pd.DataFrame()

if _corr_summary.empty:
    st.warning(
        "Live summary unavailable (query failed or returned no data). "
        "By definition, `correlation_state` is `STRONG_RELATIONSHIP` at "
        "`ABS(rolling_pressure_corr) >= 0.82` and `MODERATE_RELATIONSHIP` at "
        "`>= 0.55` (`protocol_repression_correlation_mart.sql`)."
    )
else:
    _row = _corr_summary.iloc[0]
    _total = int(_row["total_rows"])
    _qualifying = int(_row["qualifying_rows"])
    _max_abs_corr = float(_row["max_abs_corr"])
    _max_damping = float(_row["max_damping"])
    _as_of = pd.Timestamp(_row["snapshot_at"]).strftime("%Y-%m-%d %H:%M UTC")

    st.markdown(f"""
    As of **{_as_of}**, across this mart's full history ({_total:,}
    protocol-day rows): **{_qualifying} of {_total}** rows have ever reached
    the MODERATE (>=0.55) or STRONG (>=0.82) correlation threshold. The
    largest magnitude `rolling_pressure_corr` observed, ever, is
    **{_max_abs_corr:.2f}**.

    These thresholds are mathematically reachable -- the quality/confidence
    damping product (`sample_quality_score x final_confidence_score`) has
    reached as high as **{_max_damping:.2f}**, above the STRONG threshold --
    but no protocol-day row in this pipeline's history has actually crossed
    either threshold yet.

    **0.55 and 0.82 are inherited default thresholds. They have never been
    independently calibrated against Kenya's actual pilot data, and are not
    adjusted here to make more windows qualify** -- lowering them to produce
    more "findings" would misrepresent what the data shows, which is the
    opposite of what this disclosure is for.
    """)

st.divider()


# ============================================================
# LIMITATIONS
# ============================================================

st.subheader("Known Analytical Constraints")

st.warning("""
This framework measures **observable statistical behavior**.

It does **not** prove legal intent or operator attribution.

Interpretation should always be paired with:

- legal context
- public incident chronology
- independent technical verification
""")

st.divider()


# ============================================================
# DATA SOURCES & KNOWN LIMITATIONS
# ============================================================

st.subheader("Data Sources & Known Limitations")

st.dataframe(
    pd.DataFrame({
        "Source": [
            "OONI",
            "ACLED",
            "Google Transparency Report",
            "Lumen Database"
        ],
        "Status": [
            "Real",
            "Real",
            "Real",
            "Synthetic (fabricated)"
        ],
    }),
    use_container_width=True,
    hide_index=True
)

st.warning("""
**Lumen Database data is currently entirely synthetic, and has been
formally benched from this pipeline's scoring (ADR-0004).** It is
generated for development (`scripts/lumen_parquet.py`, a fixed random
seed), not sourced from a real Lumen export.

As of 2026-07-05, `legal_pressure_score` is no longer a term in
`composite_pressure_score` -- the composite is computed from
`conflict_pressure_score` (75%) and `platform_pressure_score` (25%)
only. `legal_pressure_score` and `legal_pressure_is_synthetic` remain
in the underlying tables (schema, CTE, and provenance-flag machinery
kept in place for a future real Lumen-equivalent), but no longer affect
any figure on the National Stress Observatory, Suppression Event
Explorer, or Finance Bill 2024 Incident Report pages.

A real, per-row `is_synthetic` flag is still carried from the staging
layer through every downstream table. Lumen will be reconsidered for
inclusion once a real Lumen export replaces the fabricated dataset.
""")

st.warning("""
**DNS canary misclassification, found and fixed 2026-08-01 (TD-68).**
This project's most-repeated flagship finding -- "177 same-day,
high-confidence DNS-layer interference signals inside Kenya on
June 25, 2024, concentrated on Signal's DNS resolution" -- was
retracted after a live cross-check against OONI's own public API.

The bogon classifier matched any DNS answer shaped like a
private/reserved IP, with no exclusion for `uptime.signal.org`,
Signal's own intentional client-side canary hostname, which is
designed to always resolve to `127.0.0.1` as a benign health check.
OONI's own Signal-test author confirmed independently: "the DNS
results with IP 127.0.0.1 are to be considered normal."

**Fixed and verified against live data:** the June 25, 2024 same-day
count is now correctly 0. The regex-bogon signal traces 100% to
`uptime.signal.org` across the full 761-day ingestion history
(49,883 rows), and the retraction holds across the entire Finance
Bill 2024 window, not just June 25.
""")

st.warning("""
**TLS handshake-success misclassification, found and fixed 2026-08-01
(TD-72).** `handshake_success` was structurally `NULL` for 100% of
the 422,487 rows in the TLS observation table, across every app
tested (Signal, WhatsApp, Telegram, Psiphon) -- a copy-paste of a
JSONPath from an unrelated data shape. As a result, 386,617 of those
422,487 rows (91.5%), every genuinely successful handshake, was
misclassifying as `UNKNOWN` instead of `OK`.

**Fixed** by deriving `handshake_success` from `tls_failure IS NULL`,
matching OONI's own canonical TLS model. **Externally validated**
against OONI's own live API: 100/100 sampled reclassified rows
confirmed present-and-null in OONI's own raw TLS handshake data, and
all 361 real `BLOCKED` rows system-wide were individually checked --
281/361 (77.8%) agree directly with OONI's own anomaly verdict, and
the remaining 80/361 were each traced to a documented OONI
known-bad-probe-version exclusion, not a genuine disagreement.
""")

attribution_footer(["ACLED", "OONI"])

st.divider()


# ============================================================
# FINAL STATEMENT
# ============================================================

st.success("""
This observability framework was designed to prioritize:

• statistical rigor  
• false-positive suppression  
• transparent inference logic  
• reproducible censorship intelligence

Every score, count, and classification shown on this dashboard is computed
at render time from the pipeline's feature, intelligence, and reporting
transformations -- none is a hardcoded value. Scope and grain disclosures
accompany each page's own data and are maintained as the pipeline evolves.
""")
