# utils/contracts.py

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date",
    "country",
    "block_rate",
    "blocked_tests",
    "conflict_events",
    "fatalities",
    "takedown_requests",
    "items_removed",
    "google_requests",
    "civil_liberties_pressure_index",
    "suppression_window",
    "political_context_flag",
    "conflict_block_overlap",
    "has_blocking",
    "has_conflict",
}

# strict alias map (fixes schema drift across pages)
COLUMN_ALIASES = {
    "suppression_window_type": "suppression_window",
    "year_month": "measurement_date",
}

def normalize_columns(df):
    """Standardise mart output across pages"""
    for old, new in COLUMN_ALIASES.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})
    return df
