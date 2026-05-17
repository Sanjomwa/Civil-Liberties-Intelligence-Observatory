# core/constants.py

"""
Global system constants for the
Kenya Civil Liberties Observatory

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

from datetime import date


# ============================================================
# APP METADATA
# ============================================================

APP_NAME = "Kenya Civil Liberties Observatory"

APP_TAGLINE = (
    "Historical observability into censorship, "
    "network interference, and civil liberties pressure "
    "(Kenya, Jun 2023 – Jun 2025)"
)

APP_VERSION = "v1.0"

COUNTRY = "Kenya"
ISO2 = "KE"


# ============================================================
# BIGQUERY PROJECT
# ============================================================

PROJECT_ID = "encoded-joy-485413-k5"

DATASETS = {
    "reporting": "reporting",
    "marts": "marts",
    "features": "features",
    "intelligence": "intelligence",
}


# ============================================================
# SCIENTIFIC OBSERVATION WINDOW
# ============================================================

DEFAULT_START = date(2023, 6, 1)
DEFAULT_END = date(2025, 6, 30)


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
