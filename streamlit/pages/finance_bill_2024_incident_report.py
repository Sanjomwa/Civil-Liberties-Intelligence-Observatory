# WITHDRAWN 2026-11: ACLED-based; do not re-list without owner decision
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, confidence_color, inject_css
from services.marts import get_finance_bill_incident
from components.status import render_confidence_badge
from components.trust import render_trust_strip, attribution_footer


ADR_0016_URL = (
    "https://github.com/Sanjomwa/Civil-Liberties-Intelligence-Observatory/"
    "blob/main/docs/02-architecture/adr/"
    "0016-episode-based-method-replaces-rolling-correlation.md"
)

RETIRED_CAPTION = (
    "Retired pending removal (ADR-0016): this rolling correlation is no "
    "longer used for findings."
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

# Item 29 (2026-11-16): the second result (the per-ASN profile) is no longer
# displayed on this page; the query function is unchanged.
df, _asn_df = get_finance_bill_incident()

if df.empty:
    st.warning("No Finance Bill 2024 data available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# FIGURES USED IN THE TEXT (computed, never hardcoded)
# ============================================================

total_rows = len(df)
total_days = int(df["measurement_date"].nunique())
sync_rows = int((df["alignment_state"] == "SYNCHRONIZED_ESCALATION").sum())
strong_or_moderate_rows = int(
    df["correlation_state"].isin(["STRONG_RELATIONSHIP", "MODERATE_RELATIONSHIP"]).sum()
)
zero_variance_rows = int((df["correlation_state"] == "ZERO_VARIANCE_WINDOW").sum())
weak_rows = int((df["correlation_state"] == "WEAK_OR_NO_RELATIONSHIP").sum())
max_abs_corr = df["rolling_pressure_corr"].abs().max()
alignment_counts = df["alignment_state"].value_counts()
correlation_counts = df["correlation_state"].value_counts()


# ============================================================
# HEADER
# ============================================================

st.title("Finance Bill 2024: what the retired correlation method showed")

render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# WHAT THIS PAGE SHOWS
# ============================================================

if sync_rows == 0 and strong_or_moderate_rows == 0:
    result_sentence = (
        "The method found no alignment in this period."
    )
else:
    result_sentence = (
        "The method's labels are reported below exactly as computed."
    )

st.info(
    f"This page shows the result of the rolling OONI–pressure correlation "
    f"for the Finance Bill 2024 protest period. CLIO retired this method in "
    f"[ADR-0016]({ADR_0016_URL}).\n\n"
    f"{result_sentence} Of {total_rows} protocol-day rows ({total_days} "
    f"days), **{sync_rows}** were labelled `SYNCHRONIZED_ESCALATION` and "
    f"**{strong_or_moderate_rows}** reached the moderate (0.55) or strong "
    f"(0.82) correlation threshold. The largest correlation magnitude in "
    f"the window was **{max_abs_corr:.2f}**.\n\n"
    "This result is reported because CLIO reports results whatever they show."
)

st.warning(
    "The disruption on 25 June 2024 was mainly a drop in connectivity. "
    "OONI's app tests largely cannot see a connectivity drop, so this page "
    "cannot assess that disruption."
)

st.markdown(
    "Full label breakdown for this window. Alignment: "
    + ", ".join(f"{v} {k}" for k, v in alignment_counts.items())
    + ". Correlation strength: "
    + ", ".join(f"{v} {k}" for k, v in correlation_counts.items())
    + "."
)

st.divider()


# ============================================================
# COMPOSITE PRESSURE INDEX
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
    "Composite pressure index, daily, Finance Bill 2024 window"
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Plots `composite_pressure_score`: a log-scaled index built from ACLED "
    "weekly conflict data (75%) and Google Transparency Report data (25%). "
    "It moves in weekly steps. It does not include OONI data."
)

st.divider()


# ============================================================
# ROLLING CORRELATION BY PROTOCOL AND DAY
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
    "Rolling OONI–pressure correlation, by protocol and day"
)

st.caption(RETIRED_CAPTION)
st.plotly_chart(sync, use_container_width=True)

_window_min = df["rolling_pressure_corr"].min()
_window_max = df["rolling_pressure_corr"].max()

st.markdown(f"""
Color scale fixed to [-1, 1] so shading reflects the real magnitude of
`rolling_pressure_corr`, not this window's own narrow range. Values in this
window run **{_window_min:.2f} to {_window_max:.2f}** -- well below the 0.55
moderate threshold on this same scale. Each cell is one protocol's own
correlation with the composite pressure index, computed independently of
every other protocol.
""")

st.divider()


# ============================================================
# ALIGNMENT STATE LABELS
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
    "Alignment state labels, count of protocol-day rows"
)

st.caption(RETIRED_CAPTION)
st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ============================================================
# PROTOCOL STRESS VS COMPOSITE INDEX
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
    "OONI protocol stress score vs. composite pressure index, per protocol-day"
)

st.plotly_chart(fig3, use_container_width=True)

st.caption(
    "Each point is one protocol on one day. Colour is the `divergence_state` "
    "label from the same retired correlation mart."
)

st.divider()


# ============================================================
# STRONGEST CORRELATION VALUES
# ============================================================

qualifying = df[
    df["correlation_state"].isin([
        "STRONG_RELATIONSHIP",
        "MODERATE_RELATIONSHIP"
    ])
]

if not qualifying.empty:
    st.subheader("Protocol-day rows at or above the moderate threshold")
    st.markdown(
        f"**{len(qualifying)} of {total_rows}** protocol-day rows in this window "
        "reach the strong or moderate correlation threshold. Shown below, sorted "
        "by correlation magnitude."
    )
    display_rows = qualifying.sort_values(
        "rolling_pressure_corr", key=lambda s: s.abs(), ascending=False
    )
else:
    st.subheader("Largest correlation values in this window (none reached the moderate threshold)")
    st.markdown(f"""
    **No protocol-day row in this window reaches the moderate (>=0.55) or strong
    (>=0.82) correlation threshold.** The largest observed here is
    **{max_abs_corr:.2f}**. Of {total_rows} protocol-day rows: **{weak_rows}**
    are `WEAK_OR_NO_RELATIONSHIP` (a computable but weak correlation) and
    **{zero_variance_rows}** are `ZERO_VARIANCE_WINDOW` (correlation undefined,
    not merely weak -- zero variance in the underlying series over the rolling
    window). The table below shows the {min(20, len(df))} rows with the largest
    correlation magnitude, sorted by `ABS(rolling_pressure_corr)` to match the
    mart's own threshold definition.
    """)
    display_rows = df.sort_values(
        "rolling_pressure_corr", key=lambda s: s.abs(), ascending=False
    ).head(20)

st.caption(RETIRED_CAPTION)
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

st.divider()


# ============================================================
# RESULT
# ============================================================

st.subheader("Result")

if strong_or_moderate_rows > 0:
    st.markdown(f"""
    **{strong_or_moderate_rows} of {total_rows}** protocol-day rows in this
    window reach the strong or moderate correlation threshold of the retired
    method.
    """)
else:
    st.markdown(f"""
    No protocol-day row in this window reaches the strong (>=0.82) or
    moderate (>=0.55) correlation threshold of the retired method; the
    largest observed is **{max_abs_corr:.2f}**. This is a null result for
    this method. It is not evidence about whether interference did or did
    not happen.
    """)

st.caption(
    "These thresholds (strong >= 0.82, moderate >= 0.55) have never been "
    "reached in this mart's full history either -- see **Methodology & "
    "Statistical Guardrails** for the complete disclosure."
)

_confidence_series = df["final_confidence_level"].dropna()
modal_confidence = _confidence_series.mode().iloc[0] if not _confidence_series.empty else None

render_confidence_badge(
    "Retired mart's confidence label (modal)",
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
