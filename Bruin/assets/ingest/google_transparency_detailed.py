"""@bruin

description: this is a python asset

@bruin"""

# @bruin
# name: raw.google_transparency_detailed
# type: python
# connection: duckdb-google
# description: Ingest Google Transparency detailed removal requests CSV into raw table and export as Parquet
# owner: civil-liberties-pipeline
# @bruin

import duckdb
import os


def ingest_google_transparency_detailed():
    # Explicit file path for DuckDB database (persistent)
    db_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/civil_liberties_dev.db"
    conn = duckdb.connect(db_path)

    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/google/"
    detailed_csv = os.path.join(
        base_path, "google-government-detailed-removal-requests.csv")
    parquet_out = os.path.join(
        base_path, "google_transparency_detailed.parquet")

    conn.execute("CREATE SCHEMA IF NOT EXISTS dev_raw;")

    conn.execute("""
        CREATE OR REPLACE TABLE dev_raw.google_transparency_detailed AS
        SELECT 
            "Country/Region" AS country_region,
            "Period Ending" AS period_ending,
            Product,
            Reason,
            Total,
            CURRENT_TIMESTAMP AS extracted_at
        FROM read_csv_auto(?)
    """, [detailed_csv])

    # Export to Parquet for durability
    conn.execute(
        f"COPY dev_raw.google_transparency_detailed TO '{parquet_out}' (FORMAT PARQUET)")

    print("✅ Created dev_raw.google_transparency_detailed and exported to", parquet_out)
    conn.close()


if __name__ == "__main__":
    ingest_google_transparency_detailed()
