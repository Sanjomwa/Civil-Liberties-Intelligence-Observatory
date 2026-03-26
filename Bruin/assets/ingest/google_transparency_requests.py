"""@bruin

description: this is a python asset

@bruin"""

# @bruin
# name: raw.google_transparency_requests
# type: python
# connection: duckdb-google
# description: Ingest Google Transparency requests CSV into raw table and export as Parquet
# owner: civil-liberties-pipeline
# @bruin

import duckdb
import os


def ingest_google_transparency_requests():
    # Explicit file path for DuckDB database (persistent)
    db_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/civil_liberties_dev.db"
    conn = duckdb.connect(db_path)

    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/"
    requests_csv = os.path.join(
        base_path, "google-government-removal-requests.csv")
    parquet_out = os.path.join(
        base_path, "google_transparency_requests.parquet")

    conn.execute("CREATE SCHEMA IF NOT EXISTS dev_raw;")

    conn.execute("""
        CREATE OR REPLACE TABLE dev_raw.google_transparency_requests AS
        SELECT 
            country,
            product,
            reason,
            time_period,
            number_of_requests,
            items_requested_removal,
            CURRENT_TIMESTAMP AS extracted_at
        FROM read_csv_auto(?)
    """, [requests_csv])

    # Export to Parquet for durability
    conn.execute(
        f"COPY dev_raw.google_transparency_requests TO '{parquet_out}' (FORMAT PARQUET)")

    print("✅ Created dev_raw.google_transparency_requests and exported to", parquet_out)
    conn.close()


if __name__ == "__main__":
    ingest_google_transparency_requests()
