# utils/contracts.py

# ─────────────────────────────────────────────
# CORE MART (PRIMARY SPINE)
# ─────────────────────────────────────────────

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date": "date",
    "country": "string",

    # OONI
    "ooni_tests": "int",
    "blocked_tests": "int",
    "block_rate": "float",
    "network_block_signals": "int",

    # Conflict
    "conflict_events": "int",
    "fatalities": "int",

    # Pressure
    "takedown_requests": "int",
    "items_removed": "int",
    "google_requests": "int",

    # Derived features
    "civil_liberties_pressure_index": "float",
    "suppression_window": "string",

    # Stability flags (IMPORTANT FOR ALL PAGES)
    "has_blocking": "bool",
    "has_conflict": "bool",
    "conflict_block_overlap": "bool",
}


# ─────────────────────────────────────────────
# PLATFORM MART (SECONDARY SPINE)
# ─────────────────────────────────────────────

PLATFORM_CENSORSHIP_MART_SCHEMA = {
    "measurement_date": "date",
    "platform": "string",

    "block_rate": "float",
    "blocked": "int",
    "tests": "int",

    "takedown_requests": "int",
    "items_removed": "int",

    "platform_pressure_score": "float",
}


# ─────────────────────────────────────────────
# FACT TABLE CONTRACTS (EXPLORATION ONLY)
# ─────────────────────────────────────────────

FACT_CONTRACTS = {
    "fact_takedown_requests": [
        "source",
        "platform",
        "reason",
        "requestor_name",
        "number_of_requests"
    ],

    "fact_conflict_events": [
        "event_date",
        "country",
        "event_count",
        "fatalities"
    ]
}
