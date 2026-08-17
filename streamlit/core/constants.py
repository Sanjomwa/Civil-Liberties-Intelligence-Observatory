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

APP_NAME = "CLIO — Civil Liberties Intelligence Observatory"

APP_TAGLINE = (
    "Observability into censorship, network interference, and civil "
    f"liberties pressure ({COUNTRY} pilot; network/platform data currently "
    "covers Jun 2023 – Jun 2025, ACLED coverage extends to 1997 – 2026)"
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
FEATURES = f"{PROJECT_ID}.{DATASETS['features']}"
DEFAULT_START = DEFAULT_START
DEFAULT_END = DEFAULT_END


# ============================================================
# NATIONAL PRESSURE LEVELS
# ============================================================
# Keyed on fact_country_pressure_daily.sql's real pressure_level CASE
# (LOW/MODERATE/ELEVATED/SEVERE). Replaces the retired STRESS_LEVELS map,
# whose key vocabulary (NORMAL/ELEVATED_PRESSURE/HIGH_STRESS_WINDOW/
# CRITICAL_OBSERVABILITY_WINDOW) was tied to suppression_window_class, a
# field TD-66 deleted -- that map never matched any live pressure_level
# value at either of its two callsites, so both silently rendered fallback
# gray. Same 4-color green->amber->orange->red ramp already used elsewhere
# in this palette, just remapped to the vocabulary that's actually live.

PRESSURE_LEVELS = {
    "LOW": "#2FA36B",
    "MODERATE": "#F0B34A",
    "ELEVATED": "#E8593C",
    "SEVERE": "#FF3B5C",
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
# Deliberately a separate map from PRESSURE_LEVELS: primary_regime is
# intelligence.acled_pressure_regimes' own weekly categorical taxonomy,
# not fact_country_pressure_daily's pressure_level. Ordered by the regime
# engine's own hierarchy (CRISIS=7 ... STABLE=1, see acled_pressure_regimes.sql
# CTE-11) from least to most severe.

REGIME_STATES = {
    "STABLE": "#2FA36B",
    "MOBILISATION": "#5B8DEF",
    "CONFLICT": "#A855F7",
    "REPRESSION": "#F0B34A",
    "CONTESTATION": "#EF9F27",
    "ESCALATION": "#E8593C",
    "CRISIS": "#FF3B5C",
}

# TD-96 fix (2026-08-17): CRISIS/SEVERE were both #B42318, which measured
# 2.95:1 contrast against PALETTE["bg"] (#0D0D0F) -- below the 3:1 WCAG
# floor -- and had lower luminance than CONFLICT and ESCALATION, two
# nominally-less-severe states in the same ramp. #FF3B5C clears 5.58:1
# against bg (also above ESCALATION's 5.48:1 and CONFLICT's 4.91:1, fixing
# the non-monotonic ramp) and shifts hue toward crimson/rose (~350 degrees)
# rather than a brighter version of ESCALATION's orange-red (~10 degrees),
# so the two remain visually distinguishable rather than just both being
# "bright red." Brighter same-hue reds were tried and rejected -- they all
# landed within ~1.06-1.34:1 contrast of ESCALATION, i.e. still
# near-indistinguishable by luminance. Paired with a non-color icon marker
# on the two most severe badges -- see components/status.py's
# _SEVERITY_ICONS -- since hue alone is not a reliable signal for
# colorblind readers.


# ============================================================
# CORRELATION STATES
# ============================================================
# TD-96 fix (2026-08-17): WEAK_OR_NO_RELATIONSHIP was #2FA36B, the same
# green used for "healthy"/"low" states elsewhere -- falsely reassuring,
# since CLIO's real correlation data is almost always weak (per ADR-0011,
# STRONG_RELATIONSHIP has never once occurred in Kenya's data). It is also
# a distinct epistemic state from INSUFFICIENT_HISTORY/ZERO_VARIANCE_WINDOW
# ("couldn't test it," missing data) -- "tested it, found nothing" deserves
# its own identity, not the same gray as "no data." #6B8CAE is a muted
# steel-blue: clearly not the green/amber/red severity ramp, and visibly
# distinct from the flat #6B7280 gray (contrast ratio between the two is
# 1.38:1, and #6B8CAE carries a real blue hue/saturation the neutral gray
# lacks).

CORRELATION_STATES = {
    "STRONG_RELATIONSHIP": "#E8593C",
    "MODERATE_RELATIONSHIP": "#F0B34A",
    "WEAK_OR_NO_RELATIONSHIP": "#6B8CAE",
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

# TD-99 (F5): PAGES list removed 2026-08-17 -- zero consumers anywhere in
# streamlit/ (confirmed via grep), and it had drifted stale (still listed
# "Protocol Regime Monitor" and "Suppression Event Explorer", both retired
# -- see TD-16 and TD-98 respectively). app.py's st.navigation() call is
# the actual, already-correct single source of truth for page registration
# and doesn't need a shadow copy here.
