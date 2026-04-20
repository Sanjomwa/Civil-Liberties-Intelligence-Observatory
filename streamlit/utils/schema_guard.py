# utils/schema_guard.py

import streamlit as st

class SchemaViolation(Exception):
    pass


def validate_schema(df, expected_schema: set, page_name: str):
    actual = set(df.columns)

    missing = expected_schema - actual
    extra = actual - expected_schema

    if missing:
        st.error(f"❌ [{page_name}] Missing columns: {', '.join(missing)}")
        raise SchemaViolation(f"Missing columns: {missing}")

    if extra:
        st.warning(f"⚠️ [{page_name}] Unexpected columns ignored: {', '.join(extra)}")

    return True
