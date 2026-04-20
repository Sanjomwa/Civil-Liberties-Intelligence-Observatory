CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date": "datetime64",
    "block_rate": "float",
    "blocked_tests": "float",
    "conflict_events": "float",
    "fatalities": "float",
    "takedown_requests": "float",
    "items_removed": "float",
    "google_requests": "float",
    "civil_liberties_pressure_index": "float",
    "suppression_window": "string",
}

FACT_TAKEDOWN_REQUESTS_SCHEMA = {
    "source": "string",
    "platform": "string",
    "reason": "string",
    "requestor_name": "string",
    "requestor_type": "string",
    "number_of_requests": "float",
    "items_requested_removal": "float",
}

FACT_TAKEDOWN_TRENDS_SCHEMA = {
    "year_month": "string",
    "source": "string",
    "total_requests": "float",
}

FACT_CONFLICT_EVENTS_SCHEMA = {
    "event_date": "datetime64",
    "county": "string",
    "event_count": "float",
    "fatalities": "float",
    "latitude": "float",
    "longitude": "float",
}
