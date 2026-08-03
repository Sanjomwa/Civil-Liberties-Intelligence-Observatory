"""
bigquery_lookup.py — LLM report-writer prototype (ADR-0010), live build

Live BigQuery-backed implementation of claim_check.DataContext's three
lookup callables, plus a live equivalent of deterministic_analysis.py's
analyze_window() (which itself is hardwired to
fixtures/finance_bill_2024_fixture.py and accepts no injectable data
source -- a real, pre-existing property of the copied-in offline
prototype, verified by reading the file directly, not assumed).

Column-name mapping confirmed against the live schema (`bq show --schema`)
before writing a single query here, not assumed from the offline fixture's
naming, which does not match:
  intelligence.acled_pressure_regimes.primary_regime   -> regime_label
  intelligence.acled_pressure_regimes.confidence_level -> classification_confidence
  marts.fact_country_pressure_daily.measurement_date   -> date
composite_pressure_score, pressure_level, and legal_pressure_is_synthetic
matched the fixture's field names exactly; no mapping needed for those.

Authentication: bigquery.Client(project=PROJECT_ID) using whatever ADC
identity is already active in this environment -- the same plain
convention this repo already uses (see streamlit/services/bq.py's
non-Streamlit-Cloud fallback branch), no new credential file, no new
service account.
"""

from __future__ import annotations

import os

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

REGIME_SEVERITY_ORDER = ["STABLE", "MOBILISATION", "ESCALATION", "CONFLICT", "CRISIS"]

_client = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        if not PROJECT_ID:
            raise RuntimeError(
                "GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set in the "
                "environment (this repo's .env convention) before querying BigQuery."
            )
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def lookup_regime(country: str, week_start_date: str) -> dict | None:
    """DataContext.lookup_regime -- one row from intelligence.acled_pressure_regimes."""
    query = f"""
        SELECT primary_regime, confidence_level
        FROM `{PROJECT_ID}.intelligence.acled_pressure_regimes`
        WHERE country = @country AND week_start_date = @week_start_date
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("week_start_date", "DATE", week_start_date),
    ])
    rows = list(_get_client().query(query, job_config=job_config).result())
    if not rows:
        return None
    row = rows[0]
    return {
        "regime_label": row["primary_regime"],
        "classification_confidence": row["confidence_level"],
    }


def lookup_daily(country: str, date: str) -> dict | None:
    """DataContext.lookup_daily -- one row from marts.fact_country_pressure_daily."""
    query = f"""
        SELECT composite_pressure_score, pressure_level, legal_pressure_is_synthetic
        FROM `{PROJECT_ID}.marts.fact_country_pressure_daily`
        WHERE country = @country AND measurement_date = @date
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("date", "DATE", date),
    ])
    rows = list(_get_client().query(query, job_config=job_config).result())
    if not rows:
        return None
    row = rows[0]
    return {
        "composite_pressure_score": row["composite_pressure_score"],
        "pressure_level": row["pressure_level"],
        "legal_pressure_is_synthetic": row["legal_pressure_is_synthetic"],
    }


def count_weeks_at_or_above(country: str, regime_order_min: str, week_start: str, week_end: str) -> int:
    """DataContext.count_weeks_at_or_above -- re-executes claim_check.py's
    COUNT claim as a real query, using REGIME_SEVERITY_ORDER's rank (same
    vocabulary confirmed live against the table: STABLE, MOBILISATION,
    ESCALATION, CONFLICT, CRISIS -- exact match, five distinct values)."""
    min_rank = REGIME_SEVERITY_ORDER.index(regime_order_min)
    qualifying = REGIME_SEVERITY_ORDER[min_rank:]
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.intelligence.acled_pressure_regimes`
        WHERE country = @country
          AND week_start_date BETWEEN @week_start AND @week_end
          AND primary_regime IN UNNEST(@qualifying)
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("week_start", "DATE", week_start),
        bigquery.ScalarQueryParameter("week_end", "DATE", week_end),
        bigquery.ArrayQueryParameter("qualifying", "STRING", qualifying),
    ])
    rows = list(_get_client().query(query, job_config=job_config).result())
    return int(rows[0]["n"])


def list_weeks_in_window(country: str, week_start: str, week_end: str) -> list[dict]:
    """Live equivalent of deterministic_analysis._weeks_in_window. Needed
    because analyze_window() itself imports ACLED_PRESSURE_REGIMES directly
    from the offline fixture module and takes no data-source parameter at
    all -- confirmed by reading deterministic_analysis.py directly before
    writing this, not assumed from its docstring's DataContext framing
    (which only applies to claim_check.py's three callables, not to this
    function). Returns rows shaped like the fixture's own entries so
    analyze_window_live() below can reuse identical claim-construction
    logic."""
    query = f"""
        SELECT week_start_date, primary_regime AS regime_label, confidence_level AS classification_confidence
        FROM `{PROJECT_ID}.intelligence.acled_pressure_regimes`
        WHERE country = @country AND week_start_date BETWEEN @week_start AND @week_end
        ORDER BY week_start_date
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("week_start", "DATE", week_start),
        bigquery.ScalarQueryParameter("week_end", "DATE", week_end),
    ])
    return [
        {
            "country": country,
            "week_start_date": row["week_start_date"].isoformat(),
            "regime_label": row["regime_label"],
            "classification_confidence": row["classification_confidence"],
        }
        for row in _get_client().query(query, job_config=job_config).result()
    ]


def list_days_in_window(country: str, date_start: str, date_end: str) -> list[dict]:
    """Live equivalent of deterministic_analysis._days_in_window -- same
    reasoning as list_weeks_in_window above."""
    query = f"""
        SELECT measurement_date, composite_pressure_score, pressure_level, legal_pressure_is_synthetic
        FROM `{PROJECT_ID}.marts.fact_country_pressure_daily`
        WHERE country = @country AND measurement_date BETWEEN @date_start AND @date_end
        ORDER BY measurement_date
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("date_start", "DATE", date_start),
        bigquery.ScalarQueryParameter("date_end", "DATE", date_end),
    ])
    return [
        {
            "country": country,
            "date": row["measurement_date"].isoformat(),
            "composite_pressure_score": row["composite_pressure_score"],
            "pressure_level": row["pressure_level"],
            "legal_pressure_is_synthetic": row["legal_pressure_is_synthetic"],
        }
        for row in _get_client().query(query, job_config=job_config).result()
    ]


def analyze_window_live(country: str, week_start: str, week_end: str) -> list[dict]:
    """Live-data equivalent of deterministic_analysis.analyze_window() --
    IDENTICAL claim-construction logic (same four rules, same ordering),
    sourced from list_weeks_in_window / list_days_in_window /
    count_weeks_at_or_above above instead of the offline fixture. Written
    as a parallel function rather than a modification to
    deterministic_analysis.py, since that module is one of the six core
    modules this build was instructed not to change the logic of, and its
    hardcoded fixture import (not a DataContext parameter) means it cannot
    be pointed at live data without either editing it or duplicating its
    decision logic against a live source -- this file takes the latter
    path."""
    claims: list[dict] = []
    weeks = list_weeks_in_window(country, week_start, week_end)

    for week in weeks:
        claims.append({
            "claim_type": "CLASSIFICATION",
            "country": country,
            "week_start_date": week["week_start_date"],
            "source_column": "regime_label",
            "claimed_value": week["regime_label"],
        })

    for prev_week, next_week in zip(weeks, weeks[1:]):
        if prev_week["regime_label"] != next_week["regime_label"]:
            claims.append({
                "claim_type": "TEMPORAL_ORDERING",
                "country": country,
                "before": {"week_start_date": prev_week["week_start_date"], "regime_label": prev_week["regime_label"]},
                "after": {"week_start_date": next_week["week_start_date"], "regime_label": next_week["regime_label"]},
            })

    crisis_count = count_weeks_at_or_above(country, "CRISIS", week_start, week_end)
    claims.append({
        "claim_type": "COUNT",
        "country": country,
        "regime_order_min": "CRISIS",
        "week_start": week_start,
        "week_end": week_end,
        "claimed_count": crisis_count,
    })

    days = list_days_in_window(country, week_start, week_end)
    for day in days:
        if day["pressure_level"] == "SEVERE":
            claims.append({
                "claim_type": "MAGNITUDE_BAND",
                "country": country,
                "date": day["date"],
                "claimed_band": day["pressure_level"],
            })

    return claims
