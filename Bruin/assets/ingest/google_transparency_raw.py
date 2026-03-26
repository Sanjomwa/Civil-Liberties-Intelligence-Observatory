"""@bruin

description: this is a python asset

@bruin"""

# google_transparency_raw.py
# Ingest Google Transparency Report data into staging

import duckdb
import os


def ingest_google_transparency():
    # Connect to DuckDB (dev environment)
    conn = duckdb.connect(os.getenv("DB_CONN", "civil_liberties_dev.db"))

    # Path to your subset CSV (keep small in dev)
    data_path = os.getenv("DATA_PATH", "./data/dev/")
    csv_file = os.path.join(data_path, "google_transparency_subset.csv")

    # Create or replace staging table
    conn.execute(f"""
        CREATE OR REPLACE TABLE stg_google_transparency AS
        SELECT 
            country,
            product,
            reason,
            period,
            request_count
        FROM read_csv_auto('{csv_file}')
    """)

    # Log row count for examiner proof
    result = conn.execute(
        "SELECT COUNT(*) FROM stg_google_transparency").fetchone()
    print(f"✅ Ingested {result[0]} rows into stg_google_transparency")

    conn.close()


if __name__ == "__main__":
    ingest_google_transparency()
