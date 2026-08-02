import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, inject_css
from components.trust import attribution_footer


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

days = list(range(1, 31))
baseline = [1 - (d / 40) for d in days]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=days,
    y=baseline,
    mode="lines+markers"
))

apply_layout(
    fig,
    "30-Day Historical Baseline Weighting"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.markdown("""
Each protocol is evaluated against its rolling historical norm.

This prevents:

- false alerts from isolated spikes
- static threshold bias
- protocol-specific seasonality distortion
""")

st.divider()


# ============================================================
# CONFIDENCE WEIGHTING
# ============================================================

st.subheader("Confidence Weighting Logic")

confidence = pd.DataFrame({
    "Confidence Level": [
        "HIGH",
        "MEDIUM",
        "LOW"
    ],
    "Weight Applied": [
        1.00,
        0.65,
        0.25
    ]
})

st.dataframe(
    confidence,
    use_container_width=True,
    hide_index=True
)

st.markdown("""
Low-confidence observations are mathematically suppressed
before correlation scoring.

This prevents sparse evidence from amplifying synthetic
suppression signatures.
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
        "14+ baseline days",
        "weighted confidence floor"
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

All dashboard outputs are traceable to formal feature,
intelligence, and reporting transformations.
""")
