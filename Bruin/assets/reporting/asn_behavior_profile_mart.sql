/* @bruin
tags:
  - reporting

name: reporting.asn_behavior_profile_mart
type: bq.sql
connection: bigquery-default

description: |
  Behavioral observability profile for Kenyan ASNs using normalized
  OONI-derived feature and intelligence distributions.

depends:
  - features.protocol_daily_signals
  - intelligence.protocol_relationships
  - marts.dim_asn

materialization:
  type: table
  strategy: create+replace
@bruin */


WITH observation_horizon AS (

    SELECT
        COUNT(DISTINCT measurement_date)
            AS expected_observation_days

    FROM `{{ var.project_id }}.features.protocol_daily_signals`

    WHERE country = 'KE'
),


protocol_averages AS (

    SELECT
        asn,
        protocol,

        AVG(signal_rate)
            AS avg_protocol_signal_rate,

        SUM(blocked_events)
            AS protocol_blocked_events

    FROM `{{ var.project_id }}.features.protocol_daily_signals`

    WHERE country = 'KE'

    GROUP BY asn, protocol
),


dominant_protocol AS (

    SELECT
        ranked.asn,

        ranked.protocol
            AS dominant_protocol,

        SAFE_DIVIDE(
            ranked.protocol_blocked_events,
            SUM(
                ranked.protocol_blocked_events
            ) OVER (
                PARTITION BY ranked.asn
            )
        ) AS primary_blocking_protocol_share

    FROM (

        SELECT
            *,

            ROW_NUMBER() OVER (
                PARTITION BY asn
                ORDER BY avg_protocol_signal_rate DESC
            ) AS protocol_rank

        FROM protocol_averages

    ) ranked

    WHERE ranked.protocol_rank = 1
),


protocol_metrics AS (

    SELECT
        asn,

        COUNTIF(protocol_blocked_events > 0)
            AS total_active_protocols,

        COUNTIF(protocol_blocked_events > 0)
            AS protocol_diversity_score

    FROM protocol_averages

    GROUP BY asn
),


feature_metrics AS (

    SELECT
        asn,

        COUNT(DISTINCT measurement_date)
            AS observation_days,

        MAX(measurement_date)
            AS last_data_observation_date,

        SUM(measurement_count)
            AS measurement_count,

        SUM(observation_count)
            AS observation_count,

        AVG(blocked_rate_observation_weighted)
            AS avg_blocking_rate,

        AVG(confidence_weighted_interference)
            AS avg_weighted_blocking,

        STDDEV(signal_rate)
            AS blocking_variability,

        SUM(blocked_events)
            AS total_blocked_events,

        AVG(sample_quality_score)
            AS avg_sample_quality_score,

        COUNTIF(low_sample_flag)
            AS low_sample_days,

        COUNTIF(sparse_window_flag)
            AS sparse_window_days,

        COUNTIF(zero_variance_flag)
            AS zero_variance_days,

        ANY_VALUE(feature_version)
            AS feature_version

    FROM
        `{{ var.project_id }}.features.protocol_daily_signals`

    WHERE country = 'KE'

    GROUP BY asn
),


intelligence_metrics AS (

    SELECT
        asn,

        COUNTIF(
            intelligence_state =
            'COUPLED_PROTOCOL_ESCALATION'
        ) AS coupled_escalation_days,

        COUNTIF(
            intelligence_state =
            'ISOLATED_PROTOCOL_ESCALATION'
        ) AS isolated_escalation_days,

        MAX(final_confidence_score)
            AS max_intelligence_confidence_score,

        ARRAY_AGG(
            STRUCT(
                measurement_date,
                protocol,
                intelligence_state,
                final_confidence_level,
                strongest_driver_protocol,
                strongest_driver_lag_days
            )
            ORDER BY measurement_date DESC
            LIMIT 1
        )[OFFSET(0)] AS latest_intelligence,

        ANY_VALUE(intelligence_version)
            AS intelligence_version

    FROM
        `{{ var.project_id }}.intelligence.protocol_relationships`

    WHERE country = 'KE'

    GROUP BY asn
),


scaled_features AS (

    SELECT
        f.*,
        h.expected_observation_days,

        SAFE_DIVIDE(
            f.observation_days,
            h.expected_observation_days
        ) AS coverage_ratio,

        SAFE_DIVIDE(
            f.avg_weighted_blocking,
            NULLIF(
                MAX(
                    f.avg_weighted_blocking
                ) OVER (),
                0
            )
        ) AS normalized_weighted_signal,

        LEAST(
            1.0,
            SAFE_DIVIDE(
                f.observation_days,
                90.0
            )
        ) AS evidence_maturity_score

    FROM feature_metrics f
    CROSS JOIN observation_horizon h
),


scored AS (

    SELECT
        s.*,

        ROUND(
            (
                COALESCE(
                    s.normalized_weighted_signal,
                    0
                )
                * LOG(
                    1 +
                    COALESCE(
                        s.total_blocked_events,
                        0
                    )
                )
                * s.evidence_maturity_score
            ),
            4
        ) AS maturity_adjusted_signal

    FROM scaled_features s
),


final_scores AS (

    SELECT
        s.*,

        d.asn AS display_asn,
        d.network_class,
        d.is_kenya_observability_core,
        d.censorship_sensitivity_score,

        dp.dominant_protocol,
        dp.primary_blocking_protocol_share,

        pm.total_active_protocols,
        pm.protocol_diversity_score,

        i.intelligence_version,

        COALESCE(i.coupled_escalation_days,0)
            AS coupled_escalation_days,

        COALESCE(i.isolated_escalation_days,0)
            AS isolated_escalation_days,

        i.max_intelligence_confidence_score,

        i.latest_intelligence.measurement_date
            AS latest_intelligence_date,

        i.latest_intelligence.protocol
            AS latest_protocol,

        i.latest_intelligence.intelligence_state
            AS latest_intelligence_state,

        i.latest_intelligence.final_confidence_level
            AS latest_confidence_level,

        i.latest_intelligence.strongest_driver_protocol,

        i.latest_intelligence.strongest_driver_lag_days,

        ROUND(
            (
                s.maturity_adjusted_signal
                * COALESCE(
                    d.censorship_sensitivity_score,
                    0.50
                )
                * (
                    1 +
                    COALESCE(
                        i.coupled_escalation_days,
                        0
                    ) * 0.02
                )
            ),
            4
        ) AS behavioral_priority_score,

        ROUND(
            (
                (
                    COALESCE(
                        s.coverage_ratio,
                        0
                    ) * 0.60
                )
                +
                (
                    COALESCE(
                        s.avg_sample_quality_score,
                        0
                    ) * 0.40
                )
            ),
            4
        ) AS data_reliability_score

    FROM scored s

    LEFT JOIN `{{ var.project_id }}.marts.dim_asn` d
        ON CAST(s.asn AS STRING)
        = CAST(d.asn_numeric AS STRING)

    LEFT JOIN dominant_protocol dp
        ON s.asn = dp.asn

    LEFT JOIN protocol_metrics pm
        ON s.asn = pm.asn

    LEFT JOIN intelligence_metrics i
        ON s.asn = i.asn
)


SELECT
    fs.*,

    CASE
        WHEN behavioral_priority_score >= 1.00 THEN 'HIGH_SIGNAL_PROVIDER'
        WHEN behavioral_priority_score >= 0.35 THEN 'ELEVATED_SIGNAL_PROVIDER'
        WHEN behavioral_priority_score >= 0.05 THEN 'VARIABLE_BEHAVIOR'
        ELSE 'STABLE'
    END AS behavioral_class,

    CASE
        WHEN avg_weighted_blocking >= 0.0035 THEN 'VERY_HIGH'
        WHEN avg_weighted_blocking >= 0.0025 THEN 'HIGH'
        WHEN avg_weighted_blocking >= 0.0015 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS censorship_intensity_tier,

    CASE
        WHEN network_class='MAJOR_KENYA_PROVIDER'
            AND avg_weighted_blocking>=0.0025
            AND data_reliability_score>=0.70
        THEN 'High blocking signal on major provider with strong evidence coverage'

        WHEN avg_weighted_blocking>=0.0035
            AND coverage_ratio<0.20
        THEN 'Very high blocking intensity observed with limited evidence coverage'

        WHEN coupled_escalation_days>=10
        THEN 'Frequent multi-protocol escalation behavior detected'

        WHEN data_reliability_score<0.35
        THEN 'Observed blocking signals have low reliability and sparse coverage'

        WHEN avg_weighted_blocking>=0.0025
        THEN 'Elevated blocking activity observed across monitored protocols'

        ELSE 'Relatively stable observable network behavior'
    END AS summary_insight,

    'asn_behavior_profile_mart_v7_1'
        AS reporting_version,

    CURRENT_TIMESTAMP()
        AS snapshot_at

FROM final_scores fs

ORDER BY behavioral_priority_score DESC