import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.kpis import metric_row
from components.status import render_state_badge, render_confidence_badge
from components.trust import render_trust_strip, attribution_footer
from core.config import COUNTRY
from core.filters import render_sidebar
from core.state import init_state
from core.theme import apply_layout, stress_color, protocol_color, confidence_color, inject_css
from services.marts import get_protocol_regimes, get_protocol_blocking_summary


inject_css()


def _ensure_protocol_intelligence_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make the page resilient to mart versions with partial protocol fields."""

    normalized = df.copy()

    if "protocol_stress_score" not in normalized.columns:
        if "anomaly_score" in normalized.columns:
            normalized["protocol_stress_score"] = normalized["anomaly_score"]
        else:
            normalized["protocol_stress_score"] = pd.NA

    defaults = {
        "protocol_state": "UNKNOWN",
        "confidence_level": "UNKNOWN",
        "regime_confidence": pd.NA,
        "severe_obs_share": 0.0,
        "elevated_obs_share": 0.0,
        "insufficient_obs_share": 0.0,
    }

    for column, default in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default

    for column in [
        "protocol_stress_score",
        "regime_confidence",
        "severe_obs_share",
        "elevated_obs_share",
        "insufficient_obs_share",
    ]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    return normalized


def _format_number(value, fallback: str = "N/A") -> str:
    if pd.isna(value):
        return fallback
    return f"{float(value):.2f}"


init_state()
render_sidebar()


df = get_protocol_regimes(
    st.session_state.start_date,
    st.session_state.end_date,
)

if df.empty:
    st.warning("No protocol regime data available.")
    st.stop()

df = _ensure_protocol_intelligence_columns(df)
latest_date = df["date_key"].max()
latest_all_protocols = df[df["date_key"] == latest_date]


st.title("🔗 Protocol Intelligence")

st.caption(
    f"Protocol-level regime classification, anomaly pressure, and statistical "
    f"confidence across {COUNTRY}'s censorship surface (data currently covers "
    f"June 2023 – June 2025). Consolidates the former Protocol Regime Monitor "
    f"and Protocol Stress Intelligence Observatory pages (TD-16) — both read "
    f"the same underlying mart; this page removes the duplication rather than "
    f"just relocating it."
)

render_trust_strip(
    reporting_version=latest_all_protocols.iloc[0]["reporting_version"],
    snapshot_at=latest_all_protocols.iloc[0]["snapshot_at"],
    max_date=latest_date,
)

st.divider()

metric_row([
    (
        "Protocols Monitored",
        f"{latest_all_protocols['protocol'].nunique()}",
    ),
    (
        "Elevated Protocols",
        f"{(latest_all_protocols['trend_state'] == 'HIGH_PROTOCOL_ANOMALY').sum()}",
    ),
    (
        "Critical Shifts",
        f"{(latest_all_protocols['trend_state'] == 'CRITICAL_PROTOCOL_SHIFT').sum()}",
    ),
    (
        "Average Confidence",
        _format_number(latest_all_protocols["regime_confidence"].mean()),
    ),
])

st.divider()

protocol = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].dropna().unique()),
)

protocol_df = df[df["protocol"] == protocol].sort_values("date_key")
latest_protocol = protocol_df.iloc[-1]

c1, c2, c3 = st.columns(3)

c1.metric("Stress Score", _format_number(latest_protocol["protocol_stress_score"]))

with c2:
    render_state_badge(
        "Current State",
        latest_protocol["protocol_state"],
        protocol_color(latest_protocol["protocol_state"]),
    )

with c3:
    render_confidence_badge(
        "Confidence",
        latest_protocol["confidence_level"],
        confidence_color(latest_protocol["confidence_level"]),
    )

st.divider()

tab_regime, tab_reliability = st.tabs([
    "Stress Heatmap & Regime Ranking",
    "Reliability & Per-App Breakdown",
])

with tab_regime:
    st.subheader("Protocol Stress Heatmap")

    st.markdown("""
    This heatmap shows protocol-level digital stress over time across every
    monitored protocol at once. Higher intensity means stronger statistically
    abnormal interference behavior compared to historical baseline
    performance. Bright regions indicate possible coordinated protocol
    disruption.
    """)

    heat = df.pivot_table(
        index="protocol",
        columns="date_key",
        values="protocol_stress_score",
    )

    fig_heat = go.Figure(
        data=go.Heatmap(z=heat.values, x=heat.columns, y=heat.index)
    )
    apply_layout(fig_heat, "Protocol Stress Over Time")
    fig_heat.update_layout(height=500, xaxis_title="Date", yaxis_title="Protocol")
    st.plotly_chart(fig_heat, use_container_width=True)

    st.divider()

    st.subheader(f"{protocol} Regime Evolution")

    st.markdown(
        f"Detailed regime evolution for **{protocol}**: stress score, anomaly "
        "behavior, and confidence-adjusted reliability."
    )

    fig_detail = go.Figure()
    fig_detail.add_trace(go.Scatter(
        x=protocol_df["date_key"],
        y=protocol_df["protocol_stress_score"],
        name="Stress Score",
        line=dict(color="#E8593C", width=3),
    ))
    if "anomaly_score" in protocol_df.columns:
        fig_detail.add_trace(go.Scatter(
            x=protocol_df["date_key"],
            y=protocol_df["anomaly_score"],
            name="Anomaly Score",
            line=dict(color="#2EC4B6", dash="dash"),
        ))
    apply_layout(fig_detail, f"{protocol} Stress & Anomaly")
    fig_detail.update_layout(xaxis_title="Date", yaxis_title="Score")
    st.plotly_chart(fig_detail, use_container_width=True)

    fig_conf = go.Figure()
    fig_conf.add_trace(go.Bar(
        x=protocol_df["date_key"],
        y=protocol_df["regime_confidence"],
        marker_color=[stress_color(v) for v in protocol_df["protocol_state"]],
        name="Confidence",
    ))
    apply_layout(fig_conf, f"{protocol} Statistical Confidence")
    fig_conf.update_layout(xaxis_title="Date", yaxis_title="Confidence")
    st.plotly_chart(fig_conf, use_container_width=True)

    st.divider()

    st.subheader("Current Protocol Ranking")

    st.markdown(
        "Protocols ranked by current interference stress score — identifies "
        "which protocol families are experiencing the strongest censorship "
        "pressure right now."
    )

    ranked = latest_all_protocols.sort_values("protocol_stress_score", ascending=False)
    st.dataframe(
        ranked[[
            "protocol",
            "protocol_state",
            "state_driving_family",
            "protocol_stress_score",
            "regime_confidence",
            "severe_obs_share",
            "elevated_obs_share",
            "insufficient_obs_share",
            "sample_quality_score",
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "state_driving_family names which test family (dns = dedicated "
        "dnscheck resolver testing; messaging / circumvention = DNS/TCP/TLS/"
        "HTTP checks embedded in app-specific tests) triggered the protocol "
        "state. Shares are computed within each family's own volume, never "
        "pooled across families (TD-49) — a high-volume quiet family cannot "
        "mask a small loud one, and confidence describes the driving "
        "family's evidence."
    )

with tab_reliability:
    st.subheader("Observed State Distribution")

    state_counts = protocol_df["protocol_state"].value_counts().reset_index()
    state_counts.columns = ["protocol_state", "count"]

    fig_states = px.bar(
        state_counts, x="protocol_state", y="count", color="protocol_state",
    )
    apply_layout(fig_states, f"{protocol} Observed State Distribution")
    st.plotly_chart(fig_states, use_container_width=True)
    st.info(f"Shows how often {protocol} entered each statistical regime.")

    st.divider()

    st.subheader("Observation Reliability Composition")

    fig_reliability = go.Figure()
    for column in ["severe_obs_share", "elevated_obs_share", "insufficient_obs_share"]:
        fig_reliability.add_trace(go.Scatter(
            x=protocol_df["date_key"],
            y=protocol_df[column].fillna(0),
            stackgroup="one",
            name=column,
        ))
    apply_layout(fig_reliability, f"{protocol} Observation Reliability Composition")
    st.plotly_chart(fig_reliability, use_container_width=True)
    st.info(
        "Explains why protocol states were assigned. A high insufficient "
        "share indicates sparse evidence."
    )

    st.divider()

    st.subheader("Per-App, Per-Protocol-Layer Blocking Breakdown")

    st.markdown(
        """
        Full-resolution breakdown by individual app (`test_name`) and protocol
        layer, at monthly grain -- the one place in the pipeline where per-app
        attribution (Telegram vs. WhatsApp vs. Signal vs. Psiphon) survives
        without being collapsed into a coarser family label.
        """
    )

    blocking_df = get_protocol_blocking_summary(
        st.session_state.start_date,
        st.session_state.end_date,
    )

    if blocking_df.empty:
        st.warning("No per-app protocol blocking data available.")
    else:
        render_trust_strip(
            snapshot_at=blocking_df["extracted_at"].max(),
            max_date=blocking_df["month_date"].max(),
        )

        app_protocol_summary = blocking_df.groupby(
            ["test_name", "protocol"], as_index=False
        ).agg(
            total_experiment_results=("total_experiment_results", "sum"),
            blocking_signal_count=("blocking_signal_count", "sum"),
            dns_blocking_events=("dns_blocking_events", "sum"),
            tcp_blocking_events=("tcp_blocking_events", "sum"),
            tls_blocking_events=("tls_blocking_events", "sum"),
            http_blocking_events=("http_blocking_events", "sum"),
        )
        app_protocol_summary["blocking_signal_rate"] = (
            app_protocol_summary["blocking_signal_count"]
            / app_protocol_summary["total_experiment_results"]
        )

        fig_apps = px.bar(
            app_protocol_summary,
            x="test_name",
            y="blocking_signal_count",
            color="protocol",
            barmode="group",
        )
        apply_layout(fig_apps, "Blocking Signals by App and Protocol Layer")
        st.plotly_chart(fig_apps, use_container_width=True)
        st.info(
            "Counts real blocking events (not just observations) per app and "
            "per protocol layer -- DNS, TCP, TLS, HTTP."
        )

        st.dataframe(
            app_protocol_summary[[
                "test_name",
                "protocol",
                "total_experiment_results",
                "blocking_signal_count",
                "dns_blocking_events",
                "tcp_blocking_events",
                "tls_blocking_events",
                "http_blocking_events",
                "blocking_signal_rate",
            ]].sort_values(["test_name", "protocol"]),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

attribution_footer(["OONI"], snapshot_at=latest_all_protocols.iloc[0]["snapshot_at"])
