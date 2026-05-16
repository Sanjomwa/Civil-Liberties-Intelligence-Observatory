# services/marts.py

"""
Mart query interface
All pages access data through here
"""

from services.bq import run_query
from core.constants import PROJECT_ID


# ============================================================
# TABLE REFERENCES
# ============================================================

REPORTING = f"{PROJECT_ID}.reporting"


# ============================================================
# NATIONAL STRESS
# ============================================================

def get_national_stress(start_date, end_date):

    query = f"""
    SELECT *
    FROM `{REPORTING}.mart_political_stress_windows`
    WHERE date_key BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY date_key
    """

    return run_query(query)


# ============================================================
# PROTOCOL TRENDS
# ============================================================

def get_protocol_trends(start_date, end_date):

    query = f"""
    SELECT *
    FROM `{REPORTING}.mart_protocol_interference_trends`
    WHERE date_key BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY date_key
    """

    return run_query(query)


# ============================================================
# PROTOCOL CORRELATION
# ============================================================

def get_protocol_correlation(start_date, end_date):

    query = f"""
    SELECT *
    FROM `{REPORTING}.protocol_repression_correlation_mart`
    WHERE measurement_date
    BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY measurement_date
    """

    return run_query(query)


# ============================================================
# ASN INTELLIGENCE
# ============================================================

def get_asn_profiles():

    query = f"""
    SELECT *
    FROM `{REPORTING}.asn_behavior_profile_mart`
    ORDER BY behavioral_priority_score DESC
    """

    return run_query(query)
