/* @bruin
tags:
  - reporting

name: reporting.mart_political_stress_windows
type: bq.sql
connection: bigquery-default

description: |
  Detects elevated digital suppression windows in Kenya by combining
  country-level pressure indicators with statistically validated OONI
  protocol interference trends.

  This v4 rebuild corrects protocol feature collinearity by reducing
  corroboration overweighting between protocol stress and elevated
  protocol count.

depends:
  - reporting.mart_protocol_interference_trends
  - marts.fact_country_pressure_daily
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH network AS (

    SELECT
        date_key AS measurement_date,

        AVG(signal_rate) AS signal_rate,

        AVG(confidence_weighted_interference)
            AS weighted_blocking,

        MAX(anomaly_score)
            AS max_protocol_anomaly_score,

        MAX(protocol_stress_score)
            AS max_protocol_stress_score,

        COUNTIF(trend_state IN (
            'CRITICAL_PROTOCOL_SHIFT',
            'HIGH_PROTOCOL_ANOMALY'
        )) AS elevated_protocol_count,

        AVG(sample_quality_score)
            AS avg_sample_quality_score

    FROM `{{ var.project_id }}.reporting.mart_protocol_interference_trends`

    GROUP BY measurement_date
),

country_pressure AS (

    SELECT
        measurement_date,

        conflict_pressure_score,
        legal_pressure_score,
        platform_pressure_score,

        composite_pressure_score
            AS source_composite_pressure_score,

        pressure_level
            AS source_pressure_level

    FROM `{{ var.project_id }}.marts.fact_country_pressure_daily`

    WHERE iso2 = 'KE'
),

base AS (

    SELECT
        d.date_key,

        COALESCE(c.conflict_pressure_score, 0)
            AS conflict_pressure,

        COALESCE(c.legal_pressure_score, 0)
            AS legal_pressure,

        COALESCE(c.platform_pressure_score, 0)
            AS platform_pressure,

        COALESCE(c.source_composite_pressure_score, 0)
            AS source_composite_pressure_score,

        COALESCE(c.source_pressure_level, 'LOW')
            AS source_pressure_level,

        COALESCE(n.signal_rate, 0)
            AS signal_rate,

        COALESCE(n.weighted_blocking, 0)
            AS weighted_blocking,

        COALESCE(n.max_protocol_anomaly_score, 0)
            AS max_protocol_anomaly_score,

        COALESCE(n.max_protocol_stress_score, 0)
            AS max_protocol_stress_score,

        COALESCE(n.elevated_protocol_count, 0)
            AS elevated_protocol_count,

        COALESCE(n.avg_sample_quality_score, 0)
            AS avg_sample_quality_score

    FROM `{{ var.project_id }}.marts.dim_dates` d

    LEFT JOIN country_pressure c
        ON d.date_key = c.measurement_date

    LEFT JOIN network n
        ON d.date_key = n.measurement_date
),

scored AS (

    SELECT
        *,

        ROUND(
            source_composite_pressure_score
            + signal_rate * 5
            + weighted_blocking * 8
            + COALESCE(max_protocol_stress_score, 0) * 0.04
            + elevated_protocol_count * 0.18
            - (1 - avg_sample_quality_score) * 1.2,
            4
        ) AS composite_pressure_score

    FROM base
),

windowed AS (

    SELECT
        *,

        AVG(composite_pressure_score)
        OVER (
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS rolling_baseline_pressure,

        COUNT(composite_pressure_score)
        OVER (
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS baseline_days_30d

    FROM scored
),

finalized AS (

    SELECT
        *,

        ROUND(
            composite_pressure_score
            - rolling_baseline_pressure,
            4
        ) AS pressure_delta,

        CASE
            WHEN baseline_days_30d < 14
                THEN NULL

            ELSE ROUND(
                1 / (
                    1 + EXP(
                        -(
                            composite_pressure_score
                            - rolling_baseline_pressure
                        )
                    )
                ),
                4
            )
        END AS suppression_window_probability

    FROM windowed
)

SELECT
    date_key,

    conflict_pressure,
    legal_pressure,
    platform_pressure,

    source_composite_pressure_score,
    source_pressure_level,

    signal_rate,
    weighted_blocking,

    max_protocol_anomaly_score,
    max_protocol_stress_score,
    elevated_protocol_count,

    avg_sample_quality_score,

    composite_pressure_score,
    rolling_baseline_pressure,
    baseline_days_30d,

    pressure_delta,
    suppression_window_probability,

    CASE
        WHEN baseline_days_30d < 14
            THEN 'INSUFFICIENT_HISTORY'

        WHEN pressure_delta >= 1.2
            THEN 'CRITICAL_OBSERVABILITY_WINDOW'

        WHEN pressure_delta >= 0.7
            THEN 'HIGH_STRESS_WINDOW'

        WHEN pressure_delta >= 0.35
            THEN 'ELEVATED_PRESSURE'

        ELSE 'NORMAL'
    END AS suppression_window_class,

    'political_stress_windows_mart_v4'
        AS reporting_version,

    CURRENT_TIMESTAMP()
        AS snapshot_at

FROM finalized

ORDER BY date_key