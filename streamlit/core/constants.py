# core/constants.py

"""
Global system constants for the Civil Liberties Observatory

Single source of truth for:

- App metadata
- Dataset references
- Scientific observation window
- Stress semantics
- Confidence semantics
- Correlation semantics
- Protocol state semantics
- Page registry
"""

from core.config import COUNTRY, DATASETS, DEFAULT_END, DEFAULT_START, ISO2, PROJECT_ID


# ============================================================
# APP METADATA
# ============================================================

APP_NAME = f"{COUNTRY} Civil Liberties Observatory"

APP_TAGLINE = (
    "Historical observability into censorship, "
    "network interference, and civil liberties pressure "
    f"({COUNTRY}, Jun 2023 – Jun 2025)"
)

APP_VERSION = "v1.0"


# ============================================================
# BIGQUERY PROJECT
# ============================================================

# These values are driven by streamlit/core/config.py and by environment variables.


# ============================================================
# SCIENTIFIC OBSERVATION WINDOW
# ============================================================

# These values are also driven by streamlit/core/config.py and by environment variables.


# Re-export config values so downstream modules can remain unchanged.

COUNTRY = COUNTRY
ISO2 = ISO2
PROJECT_ID = PROJECT_ID
DATASETS = DATASETS
REPORTING = f"{PROJECT_ID}.{DATASETS['reporting']}"
MARTS = f"{PROJECT_ID}.{DATASETS['marts']}"
DEFAULT_START = DEFAULT_START
DEFAULT_END = DEFAULT_END


# ============================================================
# NATIONAL STRESS STATES
# ============================================================

STRESS_LEVELS = {
    "NORMAL": "#2FA36B",
    "ELEVATED_PRESSURE": "#F0B34A",
    "HIGH_STRESS_WINDOW": "#E8593C",
    "CRITICAL_OBSERVABILITY_WINDOW": "#B42318",
    "INSUFFICIENT_HISTORY": "#6B7280",
}


# ============================================================
# PROTOCOL STATES
# ============================================================

PROTOCOL_STATES = {
    "NORMAL_RANGE": "#2FA36B",
    "BELOW_BASELINE": "#5B8DEF",
    "ELEVATED": "#F0B34A",
    "SEVERE_ELEVATION": "#E8593C",
    "INSUFFICIENT_DATA": "#6B7280",
}


# ============================================================
# CONFIDENCE STATES
# ============================================================

CONFIDENCE_LEVELS = {
    "HIGH": "#2FA36B",
    "MEDIUM": "#F0B34A",
    "LOW": "#E8593C",
    "INSUFFICIENT_DATA": "#6B7280",
}


# ============================================================
# ACLED PATH A REGIME STATES (ADR-0002 step (e))
# ============================================================
# Deliberately a separate map from STRESS_LEVELS: primary_regime is
# intelligence.acled_pressure_regimes' own weekly categorical taxonomy,
# not path B's suppression_window_class. Ordered by the regime engine's
# own hierarchy (CRISIS=7 ... STABLE=1, see acled_pressure_regimes.sql
# CTE-11) from least to most severe.

REGIME_STATES = {
    "STABLE": "#2FA36B",
    "MOBILISATION": "#5B8DEF",
    "CONFLICT": "#A855F7",
    "REPRESSION": "#F0B34A",
    "CONTESTATION": "#EF9F27",
    "ESCALATION": "#E8593C",
    "CRISIS": "#B42318",
}


# ============================================================
# CORRELATION STATES
# ============================================================

CORRELATION_STATES = {
    "STRONG_RELATIONSHIP": "#E8593C",
    "MODERATE_RELATIONSHIP": "#F0B34A",
    "WEAK_OR_NO_RELATIONSHIP": "#2FA36B",
    "INSUFFICIENT_HISTORY": "#6B7280",
    "ZERO_VARIANCE_WINDOW": "#6B7280",
}


# ============================================================
# ALIGNMENT STATES
# ============================================================

ALIGNMENT_STATES = {
    "SYNCHRONIZED_ESCALATION": "#E8593C",
    "INVERSE_MOVEMENT": "#5B8DEF",
    "PROTOCOL_DIVERGENCE": "#F0B34A",
    "PRESSURE_ONLY": "#A855F7",
    "NO_CLEAR_ALIGNMENT": "#6B7280",
}


# ============================================================
# DIVERGENCE STATES
# ============================================================

DIVERGENCE_STATES = {
    "LOW_DIVERGENCE": "#2FA36B",
    "MODERATE_DIVERGENCE": "#F0B34A",
    "HIGH_DIVERGENCE": "#E8593C",
}


# ============================================================
# PAGE REGISTRY
# ============================================================

PAGES = [
    "National Stress Observatory",
    "Protocol Regime Monitor",
    "Protocol-Repression Correlation",
    "ASN Behavioral Intelligence",
    "Suppression Event Explorer",
    "Finance Bill 2024 Incident Report",
    "Methodology & Statistical Guardrails",
]
