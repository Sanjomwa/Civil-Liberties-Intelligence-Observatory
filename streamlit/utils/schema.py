"""
Central schema contract for Streamlit pages.
Prevents silent breakage when mart columns change.
"""

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date",
    "block_rate",
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
}
