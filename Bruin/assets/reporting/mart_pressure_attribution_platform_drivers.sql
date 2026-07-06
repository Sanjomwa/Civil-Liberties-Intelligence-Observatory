/* @bruin
tags:
  - reporting

name: reporting.mart_pressure_attribution_platform_drivers
type: bq.sql
connection: bigquery-default

description: |
  Pressure-attribution decomposition, platform evidence layer (ADR-0006;
  fulfills Project Zero Review Recommendation #4).

  GRAIN: one row per Google Transparency semiannual period x product x
  reason, from stg.google_transparency_detailed -- the finest breakdown
  Google publishes for content-removal requests concerning the target
  country. Each row carries its period's request-side totals
  (google_requests etc., from stg.google_transparency_requests) broadcast
  as context columns, and the period's date range, so a date can be
  mapped to its period without re-deriving the periodization.

  ATTRIBUTION ARITHMETIC:
  platform_pressure_score = LOG(1 + google_requests + detailed_total)
  in marts.fact_country_pressure_daily. As with the conflict layer, the
  LOG is nonlinear, so period_detailed_share is a share of the period's
  detailed_total (one of the two linear inputs), never a share of the
  score. google_requests is the other linear input and is not
  decomposable by product/reason (the requests dataset has no such
  breakdown) -- it is surfaced as a period-level scalar only. No
  fabricated precision.

  GRAIN HONESTY, stated bluntly because it matters to any citation:
  Google publishes this data SEMIANNUALLY. A given date's platform term
  reflects a ~6-month reporting period, broadcast across every day of
  that period (int.google_pressure_periodized). Platform evidence can
  contextualize a period; it can never explain a specific day's or
  week's movement. Within any half-year period, 100% of composite score
  movement is conflict-term movement.

  PERIODIZATION: replicates int.google_pressure_periodized's period
  construction EXACTLY (detailed period_date is a period-ENDING date,
  normalized via the month-6/month-12 CASE to the same 06-01/12-01
  anchors the requests dataset already uses; LEAD gives the exclusive
  period end). Keep the three sites in sync: int.google_pressure_periodized,
  reporting.mart_pressure_attribution_daily, and this asset.

owner: civil-liberties-pipeline

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed

materialization:
  type: table
  strategy: create+replace

columns:
  - name: period_start
    type: date
    description: Semiannual period anchor (06-01 or 12-01).
    checks:
      - name: not_null

  - name: period_detailed_share
    type: float
    description: |
      This product x reason row's share of the period's detailed_total.
      Shares within a period sum to 1. NOT a share of the (log-scale)
      platform_pressure_score.
@bruin */

WITH detailed AS (

    SELECT
        CASE
            WHEN EXTRACT(MONTH FROM period_date) = 6
                THEN DATE(EXTRACT(YEAR FROM period_date), 6, 1)
            WHEN EXTRACT(MONTH FROM period_date) = 12
                THEN DATE(EXTRACT(YEAR FROM period_date), 12, 1)
        END AS period_start,
        product,
        reason,
        SUM(total) AS removal_items

    FROM `{{ var.project_id }}.stg.google_transparency_detailed`
    GROUP BY period_start, product, reason

),

requests AS (

    SELECT
        period_date AS period_start,
        SUM(number_of_requests) AS google_requests,
        SUM(items_requested_removal) AS requested_items,
        SUM(items_removed_legal) AS legal_removed,
        SUM(items_removed_policy) AS policy_removed
    FROM `{{ var.project_id }}.stg.google_transparency_requests`
    GROUP BY period_start

),

periods AS (

    SELECT
        period_start,
        LEAD(period_start) OVER (ORDER BY period_start) AS next_period_start
    FROM (
        SELECT DISTINCT period_start FROM detailed
        WHERE period_start IS NOT NULL
        UNION DISTINCT
        SELECT DISTINCT period_start FROM requests
    )

)

SELECT
    p.period_start,
    DATE_SUB(p.next_period_start, INTERVAL 1 DAY) AS period_end,

    d.product,
    d.reason,
    d.removal_items,

    SUM(d.removal_items) OVER (PARTITION BY p.period_start)
        AS period_detailed_total,

    ROUND(
        SAFE_DIVIDE(
            d.removal_items,
            SUM(d.removal_items) OVER (PARTITION BY p.period_start)
        ),
        4
    ) AS period_detailed_share,

    ROW_NUMBER() OVER (
        PARTITION BY p.period_start
        ORDER BY d.removal_items DESC, d.product, d.reason
    ) AS period_share_rank,

    -- Request-side context, period-level scalars (no product/reason
    -- breakdown exists for these in the source).
    r.google_requests,
    r.requested_items,
    r.legal_removed,
    r.policy_removed,

    'PRESSURE_ATTRIBUTION_V1' AS attribution_methodology_version,
    'pressure_attribution_platform_drivers_v1' AS reporting_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM periods p
JOIN detailed d USING (period_start)
LEFT JOIN requests r USING (period_start)
ORDER BY p.period_start, period_share_rank
