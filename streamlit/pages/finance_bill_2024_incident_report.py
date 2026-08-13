import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, confidence_color, inject_css
from services.marts import get_finance_bill_incident
from components.status import render_confidence_badge
from components.trust import render_trust_strip, attribution_footer


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

df, asn_df = get_finance_bill_incident()

if df.empty:
    st.warning("No Finance Bill 2024 intelligence available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("📘 Finance Bill 2024 Incident Report")

st.caption(f"""
A forensic reconstruction of protocol-level suppression behavior
during {COUNTRY}'s Finance Bill 2024 protest period.

This report analyzes:

• synchronized protocol escalation  
• repression-pressure coupling  
• divergence windows  
• escalation maturity progression
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# EXEC SUMMARY
# ============================================================

st.subheader("Executive Summary")

alignment_counts = df["alignment_state"].value_counts()
correlation_counts = df["correlation_state"].value_counts()
sync_rows = int((df["alignment_state"] == "SYNCHRONIZED_ESCALATION").sum())
strong_or_moderate_rows = int(
    df["correlation_state"].isin(["STRONG_RELATIONSHIP", "MODERATE_RELATIONSHIP"]).sum()
)
crisis_days = int(
    df.loc[df["regime_primary_regime"] == "CRISIS", "measurement_date"].nunique()
)
total_days = int(df["measurement_date"].nunique())
total_rows = len(df)

st.info(f"""
**What this window's {total_rows} protocol-day rows ({total_days} days x 4 protocols) actually show:**

- Alignment: **{sync_rows} of {total_rows}** rows are `SYNCHRONIZED_ESCALATION`
  (protocol anomaly rising together with national pressure). Full breakdown: """
    + ", ".join(f"{v} {k}" for k, v in alignment_counts.items()) + f"""
- Correlation strength: **{strong_or_moderate_rows} of {total_rows}** rows reach
  `STRONG_RELATIONSHIP` or `MODERATE_RELATIONSHIP`. Full breakdown: """
    + ", ".join(f"{v} {k}" for k, v in correlation_counts.items()) + f"""
- ACLED path A (independent conflict-event classification, not derived from OONI
  protocol data): **{crisis_days} of {total_days} days** in this window are
  classified `CRISIS`.

This is a conflict-confirmed window with weak-to-absent protocol-layer
statistical correlation, not a synchronized-escalation finding. The two
evidence sources disagree on strength -- that disagreement is the honest
result, not something to resolve toward the stronger-sounding claim.
""")

st.divider()


# ============================================================
# PRESSURE TIMELINE
# ============================================================

daily = df.groupby("measurement_date").agg({
    "composite_pressure_score": "mean"
}).reset_index()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["composite_pressure_score"],
    mode="lines+markers"
))

apply_layout(
    fig,
    "National Pressure Escalation Timeline"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("""
Pressure acceleration coincides with major public
mobilization phases.
""")

st.divider()


# ============================================================
# PROTOCOL SYNCHRONIZATION
# ============================================================

sync = px.density_heatmap(
    df,
    x="measurement_date",
    y="protocol",
    z="rolling_pressure_corr",
    # Fixed to the full possible range of this value, not auto-scaled to
    # this window's own min/max -- auto-scaling would manufacture visual
    # contrast out of a narrow, weak range of real values.
    range_color=[-1, 1],
)

apply_layout(
    sync,
    "Protocol Synchronization Matrix"
)

st.plotly_chart(sync, use_container_width=True)

_window_min = df["rolling_pressure_corr"].min()
_window_max = df["rolling_pressure_corr"].max()

st.markdown(f"""
Color scale fixed to [-1, 1] so shading reflects the real magnitude of
`rolling_pressure_corr`, not this window's own narrow range. Values in this
window run **{_window_min:.2f} to {_window_max:.2f}** -- well below the 0.55
MODERATE-relationship threshold on this same scale. This heatmap does not
measure cross-protocol coordination; each cell is one protocol's own
correlation with national pressure, computed independently of every other
protocol.
""")

st.divider()


# ============================================================
# ALIGNMENT STATES
# ============================================================

align = (
    df["alignment_state"]
    .value_counts()
    .reset_index()
)

align.columns = [
    "alignment_state",
    "count"
]

fig2 = px.bar(
    align,
    x="alignment_state",
    y="count",
    color="alignment_state"
)

apply_layout(
    fig2,
    "Observed Alignment State Distribution"
)

st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ============================================================
# DIVERGENCE
# ============================================================

fig3 = px.scatter(
    df,
    x="protocol_stress_score",
    y="composite_pressure_score",
    color="divergence_state",
    hover_data=["protocol"]
)

apply_layout(
    fig3,
    "Stress Divergence Analysis"
)

st.plotly_chart(fig3, use_container_width=True)

st.markdown("""
Divergence windows reveal protocol-specific interference
outside broader pressure escalation.
""")

st.divider()


# ============================================================
# CORRELATION WINDOWS
# ============================================================

qualifying = df[
    df["correlation_state"].isin([
        "STRONG_RELATIONSHIP",
        "MODERATE_RELATIONSHIP"
    ])
]

zero_variance_rows = int((df["correlation_state"] == "ZERO_VARIANCE_WINDOW").sum())
weak_rows = int((df["correlation_state"] == "WEAK_OR_NO_RELATIONSHIP").sum())
max_abs_corr = df["rolling_pressure_corr"].abs().max()

if not qualifying.empty:
    st.subheader("High Confidence Suppression Windows")
    st.markdown(
        f"**{len(qualifying)} of {total_rows}** protocol-day rows in this window "
        "reach the STRONG or MODERATE correlation threshold. Shown below, sorted "
        "by correlation magnitude."
    )
    display_rows = qualifying.sort_values(
        "rolling_pressure_corr", key=lambda s: s.abs(), ascending=False
    )
else:
    st.subheader("Strongest Available Correlation Windows (none reached the moderate threshold)")
    st.markdown(f"""
    **No protocol-day row in this window reaches the MODERATE (>=0.55) or STRONG
    (>=0.82) correlation threshold.** The strongest observed here is
    **{max_abs_corr:.2f}**. Of {total_rows} protocol-day rows: **{weak_rows}**
    are `WEAK_OR_NO_RELATIONSHIP` (a computable but weak correlation) and
    **{zero_variance_rows}** are `ZERO_VARIANCE_WINDOW` (correlation undefined,
    not merely weak -- zero variance in the underlying series over the rolling
    window). The table below shows the {min(20, len(df))} rows with the largest
    correlation magnitude, sorted by `ABS(rolling_pressure_corr)` to match the
    mart's own threshold definition -- it is not a "high confidence" reading,
    just the closest this window comes to one.
    """)
    display_rows = df.sort_values(
        "rolling_pressure_corr", key=lambda s: s.abs(), ascending=False
    ).head(20)

st.dataframe(
    display_rows[
        [
            "measurement_date",
            "protocol",
            "rolling_pressure_corr",
            "correlation_state",
            "alignment_state",
            "divergence_state",
            "protocol_stress_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# ============================================================
# MAJOR ASN SPIKE PROFILE
# ============================================================

st.divider()

st.subheader("Major Provider ASN Spike Analysis")

st.caption("""
ASN behavior profile is a full-history snapshot (asn_behavior_profile_mart
has no date dimension) -- not scoped to the Finance Bill 2024 window like
the sections above.
""")

fig4 = px.bar(
    asn_df.sort_values(
        "behavioral_priority_score",
        ascending=False
    ),
    x="display_asn",
    y="behavioral_priority_score",
    color="avg_weighted_blocking"
)

apply_layout(
    fig4,
    f"Major {COUNTRY} Provider Suppression Signal Intensity"
)

st.plotly_chart(
    fig4,
    use_container_width=True
)

st.markdown(f"""
These are large {COUNTRY} network providers showing
elevated blocking behavior in their overall observed history,
not specifically during the Finance Bill window above.
""")

# ============================================================
# FINAL ASSESSMENT
# ============================================================

st.subheader("Statistical Assessment")

if strong_or_moderate_rows > 0:
    st.success(f"""
    **{strong_or_moderate_rows} of {total_rows}** protocol-day rows in this
    window reach the STRONG or MODERATE correlation threshold.
    """)
else:
    st.warning(f"""
    No protocol-day row in this window reaches the STRONG (>=0.82) or
    MODERATE (>=0.55) correlation threshold; the strongest observed is
    **{max_abs_corr:.2f}**. ACLED path A independently classifies
    **{crisis_days} of {total_days} days** in this window `CRISIS`. The
    conflict-event evidence and the protocol-layer correlation evidence do
    not agree in strength here -- that disagreement is the honest result,
    not a synchronized-suppression finding.
    """)

st.caption(
    "This mart's correlation-strength thresholds (STRONG >= 0.82, MODERATE "
    f">= 0.55) are not reached by any protocol-day row in this window (max "
    f"observed here: {max_abs_corr:.2f}). These thresholds have never been "
    "reached in this mart's full history either -- see **Methodology & "
    "Statistical Guardrails** for the complete disclosure."
)

_confidence_series = df["final_confidence_level"].dropna()
modal_confidence = _confidence_series.mode().iloc[0] if not _confidence_series.empty else None

render_confidence_badge(
    "Confidence level (modal)",
    modal_confidence if modal_confidence else "N/A",
    confidence_color(modal_confidence) if modal_confidence else confidence_color("INSUFFICIENT_DATA"),
)

_confidence_counts = df["final_confidence_level"].value_counts()
st.caption(
    "Modal value across this window's protocol-day rows shown above ("
    + ", ".join(f"{v} {k}" for k, v in _confidence_counts.items())
    + f" of {total_rows} total) -- not a single window-wide judgment picked "
    "without disclosing the spread."
)

st.caption(
    "TLS-derived figures on this page reflect two resolved data-quality "
    "findings (DNS canary and TLS handshake-success misclassification) "
    "-- see **Methodology & Statistical Guardrails → Data Sources & "
    "Known Limitations** for detail."
)

st.divider()

attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
