# core/constants.py

"""
Global system constants for the
Kenya Civil Liberties Observatory

Single source of truth for:

- App metadata
- Dataset references
- Stress semantics
- Confidence semantics
- Protocol state semantics
- Default filter ranges
"""

from datetime import date


# ============================================================
# APP METADATA
# ============================================================

APP_NAME = "Kenya Civil Liberties Observatory"

APP_TAGLINE = (
    "Real-time observability into censorship, "
    "network interference, and civil liberties pressure"
)

APP_VERSION = "v1.0"

COUNTRY = "Kenya"
ISO2 = "KE"


# ============================================================
# BIGQUERY
# ============================================================

PROJECT_ID = "encoded-joy-485413-k5"

DATASETS = {
    "reporting": "reporting",
    "marts": "marts",
    "features": "features",
    "intelligence": "intelligence",
}


# ============================================================
# DEFAULT DATE FILTERS
# ============================================================

DEFAULT_START = date(2023, 1, 1)
DEFAULT_END = date.today()


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
