# utils/contracts.py

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date",
    "block_rate",
    "blocked_tests",
    "conflict_events",
    "fatalities",
    "takedown_requests",
    "items_removed",
    "google_requests",
    "civil_liberties_pressure_index",
    "suppression_window",
    "has_blocking",
    "has_conflict",
    "conflict_block_overlap",
    "ooni_tests",
    "network_block_signals",
}

PLATFORM_CENSORSHIP_MART_SCHEMA = {
    "measurement_date",
    "platform",
    "block_rate",
    "blocked",
    "tests",
    "takedown_requests",
    "items_removed",
    "platform_pressure_score",
}
