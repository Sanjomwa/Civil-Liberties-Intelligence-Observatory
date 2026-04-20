# utils/contracts.py

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date": "datetime",
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

    # Derived
    "civil_liberties_pressure_index": "float",
    "suppression_window": "string",

    # Features (important for pages 3/4)
    "has_blocking": "bool",
    "has_conflict": "bool",
    "conflict_block_overlap": "bool",
}
