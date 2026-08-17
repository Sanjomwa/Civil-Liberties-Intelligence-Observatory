import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, correlation_color, alignment_color, confidence_color, inject_css
from services.marts import get_protocol_correlation, get_event_explorer
from components.charts import add_threshold_lines
from components.status import render_state_badge, render_confidence_badge
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
# TD-98: this page merges the former, separate "Suppression Event Explorer"
# page in as a second tab -- both queried reporting.protocol_repression_
# correlation_mart (get_protocol_correlation here selects directly; get_
# event_explorer adds a LEFT JOIN to mart_protocol_interference_trends for
# protocol_state/regime_confidence) and told substantially the same
# weak-correlation story in two separate nav entries. Both queries are kept
# as-is, unmerged, to avoid changing either one's column set or behavior --
# only the page-level presentation was consolidated.

df = get_protocol_correlation(
    st.session_state.start_date,
    st.session_state.end_date
)

event_df = get_event_explorer(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty and event_df.empty:
    st.warning("No protocol correlation intelligence available.")
    st.stop()

latest = df.iloc[-1] if not df.empty else event_df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("📡 Protocol ↔ Repression Correlation Engine")

st.caption("""
Measures rolling correlation between protocol-level anomaly escalation and
national repression pressure, damped by sample quality and confidence. This
is not a significance-tested statistic -- no p-value or equivalent test is
computed anywhere in this pipeline.

Two ways to explore this same mart: **Protocol Drill-Down** follows one
protocol's correlation over time; **Date Snapshot** follows every protocol
on one specific date -- useful for reconstructing what happened around a
specific incident. (TD-98: the Date Snapshot tab is merged in from the
former, separate "Suppression Event Explorer" page -- same underlying data,
two views, one honest weak-correlation disclosure instead of two.)

**Protocol anomalies here are observed as unreachable from OONI's Kenyan
measurement vantage points, not confirmed en-route interference location
(TD-95)** -- the pipeline cannot yet distinguish local Kenyan interference
from upstream/transit interference or a destination service's own
geoblocking decision. See Methodology & Statistical Guardrails for detail.
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=max(
        [d for d in [
            df["measurement_date"].max() if not df.empty else None,
            event_df["measurement_date"].max() if not event_df.empty else None,
        ] if d is not None]
    )
)

_any_qualifying_engine = bool(
    df["correlation_state"].isin(["STRONG_RELATIONSHIP", "MODERATE_RELATIONSHIP"]).any()
) if not df.empty else False
_max_abs_corr_engine = df["rolling_pressure_corr"].abs().max() if not df.empty else None

if _max_abs_corr_engine is not None:
    st.caption(
        (
            "At least one protocol-day row in the selected date range reaches "
            "the MODERATE or STRONG threshold."
            if _any_qualifying_engine
            else (
                "No protocol-day row in the selected date range reaches the "
                "MODERATE (0.55) or STRONG (0.82) threshold -- the largest "
                f"magnitude observed is {_max_abs_corr_engine:.2f}."
            )
        )
        + " See **Methodology & Statistical Guardrails** for the full, "
        "dashboard-wide disclosure of how often these thresholds have been "
        "reached historically, and why they have not been independently "
        "recalibrated against Kenya's pilot data."
    )

st.divider()


# ============================================================
# TABS
# ============================================================

tab_drilldown, tab_snapshot = st.tabs(["Protocol Drill-Down", "Date Snapshot"])


# ============================================================
# TAB 1: PROTOCOL DRILL-DOWN (former Correlation Engine content)
# ============================================================

with tab_drilldown:
    if df.empty:
        st.info("No protocol correlation intelligence available for this date range.")
    else:
        protocol = st.selectbox(
            "Select Protocol",
            sorted(df["protocol"].dropna().unique()),
            key="corr_engine_protocol",
        )

        protocol_df = df[df["protocol"] == protocol]
        latest_protocol = protocol_df.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Rolling Correlation",
            f"{latest_protocol['rolling_pressure_corr']:.2f}"
            if latest_protocol["rolling_pressure_corr"] is not None
            else "N/A"
        )

        with c2:
            render_state_badge(
                "Alignment State",
                latest_protocol["alignment_state"],
                alignment_color(latest_protocol["alignment_state"]),
            )

        with c3:
            render_state_badge(
                "Correlation Strength",
                latest_protocol["correlation_state"],
                correlation_color(latest_protocol["correlation_state"]),
            )

        with c4:
            render_confidence_badge(
                "Confidence",
                latest_protocol["final_confidence_level"],
                confidence_color(latest_protocol["final_confidence_level"]),
            )

        st.divider()

        # ----------------------------------------------------
        # ROLLING CORRELATION TIMELINE
        # ----------------------------------------------------

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=protocol_df["measurement_date"],
            y=protocol_df["rolling_pressure_corr"],
            name="Rolling Correlation",
            line=dict(width=3)
        ))

        add_threshold_lines(
            fig,
            values=[0.55, -0.55, 0.82, -0.82],
            labels=["MODERATE", "MODERATE", "STRONG", "STRONG"],
            opacity=[0.5, 0.5, 0.6, 0.6],
        )

        apply_layout(
            fig,
            f"{protocol} Rolling Pressure Correlation"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.info("""
        Positive values indicate protocol disruption rising with national pressure.

        Negative values suggest inverse movement.

        Strong sustained positive correlation is a potential synchronized
        suppression signal.
        """)

        st.divider()

        # ----------------------------------------------------
        # SYNCHRONIZED STRESS
        # ----------------------------------------------------

        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            x=protocol_df["measurement_date"],
            y=protocol_df["synchronized_stress"],
            fill="tozeroy",
            name="Synchronization Strength"
        ))

        apply_layout(
            fig2,
            "Escalation Synchronization Strength"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

        st.info("""
        Measures how consistently protocol interference and national pressure
        move together over rolling windows.
        """)

        st.divider()

        # ----------------------------------------------------
        # DIVERGENCE (time series, one protocol)
        # ----------------------------------------------------

        fig3 = go.Figure()

        fig3.add_trace(go.Bar(
            x=protocol_df["measurement_date"],
            y=protocol_df["stress_divergence"],
            name="Stress Divergence"
        ))

        apply_layout(
            fig3,
            "Protocol vs Pressure Divergence"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )

        st.info("""
        Large divergence means protocol behavior is moving independently
        from national repression pressure.

        This may indicate isolated protocol anomalies or alternate drivers.
        """)

        st.divider()

        # ----------------------------------------------------
        # ALIGNMENT DISTRIBUTION
        # ----------------------------------------------------

        align_counts = (
            protocol_df["alignment_state"]
            .value_counts()
            .reset_index()
        )

        align_counts.columns = ["alignment_state", "count"]

        fig4 = px.bar(
            align_counts,
            x="alignment_state",
            y="count",
            color="alignment_state"
        )

        apply_layout(
            fig4,
            "Observed Alignment States"
        )

        st.plotly_chart(
            fig4,
            use_container_width=True
        )

        st.divider()

        # ----------------------------------------------------
        # PROTOCOL RANKING
        # ----------------------------------------------------

        latest_all = (
            df.sort_values("measurement_date")
            .groupby("protocol")
            .tail(1)
            .sort_values(
                "rolling_pressure_corr",
                key=lambda s: s.abs(),
                ascending=False
            )
        )

        st.subheader("Current Protocol Correlation Ranking")

        st.dataframe(
            latest_all[
                [
                    "protocol",
                    "rolling_pressure_corr",
                    "correlation_state",
                    "alignment_state",
                    "final_confidence_level"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 2: DATE SNAPSHOT (former Suppression Event Explorer content)
# ============================================================

with tab_snapshot:
    if event_df.empty:
        st.info("No event intelligence available for this date range.")
    else:
        event_date = st.selectbox(
            "Select Event Date",
            sorted(event_df["measurement_date"].unique(), reverse=True),
            key="corr_engine_event_date",
        )

        event_date_df = event_df[event_df["measurement_date"] == event_date]

        # ----------------------------------------------------
        # EVENT KPIs
        # ----------------------------------------------------

        ec1, ec2, ec3, ec4, ec5 = st.columns(5)

        ec1.metric(
            "Protocols Monitored",
            len(event_date_df)
        )

        ec2.metric(
            "Avg Correlation",
            f"{event_date_df['rolling_pressure_corr'].mean():.2f}"
        )

        ec3.metric(
            "Avg Pressure",
            f"{event_date_df['composite_pressure_score'].mean():.2f}"
        )

        ec4.metric(
            "Elevated Protocols",
            int((event_date_df["protocol_state"] == "ELEVATED").sum())
        )

        ec5.metric(
            "Critical Shifts",
            int((event_date_df["protocol_state"] == "SEVERE_ELEVATION").sum())
        )

        st.divider()

        # ----------------------------------------------------
        # EVENT HEATMAP
        # ----------------------------------------------------

        heat = px.density_heatmap(
            event_date_df,
            x="protocol",
            y="alignment_state",
            z="rolling_pressure_corr",
            # Fixed to the full possible range of this value, not auto-scaled to
            # this selection's own min/max -- auto-scaling manufactures visual
            # contrast out of a narrow, weak range of real values.
            range_color=[-1, 1],
        )

        apply_layout(
            heat,
            "Protocol Alignment Heatmap"
        )

        st.plotly_chart(
            heat,
            use_container_width=True
        )

        _heat_min = event_date_df["rolling_pressure_corr"].min()
        _heat_max = event_date_df["rolling_pressure_corr"].max()

        st.markdown(f"""
        Color scale fixed to [-1, 1]. Each cell is one protocol's own correlation
        with national pressure on this date, computed independently -- this does not
        measure cross-protocol coordination. Values shown here run
        **{_heat_min:.2f} to {_heat_max:.2f}**, against a 0.55 MODERATE-relationship
        threshold on the same scale.
        """)

        st.divider()

        # ----------------------------------------------------
        # CORRELATION RANKING (this date, across protocols)
        # ----------------------------------------------------

        rank = event_date_df.sort_values(
            "rolling_pressure_corr",
            key=lambda s: s.abs(),
            ascending=False
        )

        fig_rank = px.bar(
            rank,
            x="protocol",
            y="rolling_pressure_corr",
            color="correlation_state"
        )

        apply_layout(
            fig_rank,
            "Protocol Correlation Ranking"
        )

        st.plotly_chart(
            fig_rank,
            use_container_width=True
        )

        _any_qualifying_in_range = bool(
            event_df["correlation_state"].isin(["STRONG_RELATIONSHIP", "MODERATE_RELATIONSHIP"]).any()
        )
        _range_max_abs_corr = event_df["rolling_pressure_corr"].abs().max()

        st.markdown(f"""
        Bar height is signed correlation magnitude; ranking (left to right) is by
        `ABS(rolling_pressure_corr)`, matching the mart's own STRONG/MODERATE
        threshold definition -- a strong inverse relationship ranks as high as a
        strong positive one. {"At least one protocol-day row in the selected date range reaches the MODERATE or STRONG threshold." if _any_qualifying_in_range else f"No protocol-day row in the selected date range reaches the MODERATE (0.55) or STRONG (0.82) threshold -- the largest magnitude observed is {_range_max_abs_corr:.2f}."}
        See **Methodology & Statistical Guardrails** for the full, dashboard-wide
        disclosure of how often these thresholds have been reached historically.
        """)

        st.divider()

        # ----------------------------------------------------
        # DIVERGENCE (cross-sectional scatter, this date across protocols)
        # ----------------------------------------------------

        fig_div = px.scatter(
            event_date_df,
            x="protocol_stress_score",
            y="composite_pressure_score",
            color="divergence_state",
            size="regime_confidence",
            hover_data=["protocol"]
        )

        apply_layout(
            fig_div,
            "Stress vs Pressure Divergence"
        )

        st.plotly_chart(
            fig_div,
            use_container_width=True
        )

        st.markdown("""
        Large divergence suggests protocol-specific interference
        that national pressure context alone cannot explain.
        """)

        st.divider()

        # ----------------------------------------------------
        # RAW EVENT TABLE
        # ----------------------------------------------------

        st.subheader("Event Intelligence Table")

        st.dataframe(
            event_date_df[
                [
                    "protocol",
                    "protocol_state",
                    "rolling_pressure_corr",
                    "alignment_state",
                    "correlation_state",
                    "divergence_state",
                    "protocol_stress_score",
                    "composite_pressure_score"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


st.divider()

attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
