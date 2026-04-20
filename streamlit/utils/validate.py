import streamlit as st

def validate_schema(df, expected_schema: set, page_name: str):
    """
    Hard-fail early if mart schema changes.
    Prevents silent Streamlit breakage.
    """

    missing = expected_schema - set(df.columns)

    if missing:
        st.error(f"""
        ❌ Schema mismatch in {page_name}

        Missing columns:
        {', '.join(sorted(missing))}

        Fix mart or update schema definition.
        """)
        st.stop()
