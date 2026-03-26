"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Syncs Kenya-specific JSONL files (June 2023–June 2025) and converts them to Parquet.
  Returns a Pandas DataFrame for Bruin to create/replace into DuckDB.

materialization:
  type: table
  strategy: create+replace

packages:
  - pandas

columns:
  - name: measurement_id
    type: STRING
    description: Unique OONI measurement ID
  - name: country
    type: STRING
    description: Country code (ISO two-letter)
  - name: asn
    type: INTEGER
    description: Autonomous System Number (network identifier)
  - name: test_name
    type: STRING
    description: OONI Probe test type (e.g. web_connectivity, whatsapp)
  - name: input
    type: STRING
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time (UTC)
  - name: status
    type: STRING
    description: Result status (ok, anomaly, confirmed, failure)
  - name: probe_cc
    type: STRING
    description: Country code of probe
  - name: probe_asn
    type: INTEGER
    description: ASN of probe
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import gzip
import json
import glob
import subprocess
import pandas as pd
from datetime import datetime
import os
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"

    Path(base_path).mkdir(parents=True, exist_ok=True)

    # ==================== STEP 1: Optional S3 Sync (much faster with broad patterns) ====================
    sync_needed = True
    if os.path.exists(base_path) and len(glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True)) > 50:
        print("✅ Many files already present. Skipping S3 sync (set sync_needed=True to force).")
        sync_needed = False

    if sync_needed:
        print("🚀 Starting S3 sync for Kenya OONI data (June 2023 – June 2025)... This may take several minutes.")
        sync_cmd = [
            "aws", "s3", "--no-sign-request", "sync",
            "s3://ooni-data-eu-fra/raw/", base_path,
            "--exclude", "*",
            "--include", "2023*/KE/*.jsonl.gz",   # All 2023
            "--include", "2024*/KE/*.jsonl.gz",   # All 2024
            # All 2025 (will be filtered by date later)
            "--include", "2025*/KE/*.jsonl.gz"
        ]
        try:
            result = subprocess.run(
                sync_cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            print("✅ S3 sync completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ S3 sync failed: {e}")
            raise

    # ==================== STEP 2: Process JSONL files incrementally (memory efficient) ====================
    print("📂 Finding JSONL files...")
    files = sorted(glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files)} .jsonl.gz files.")

    if not files:
        raise FileNotFoundError("No OONI JSONL files found after sync.")

    start_date = pd.Timestamp("2023-06-01")
    end_date = pd.Timestamp("2025-06-30")

    # We'll collect smaller DataFrames and concat at the end (better than list of dicts)
    dfs = []
    total_rows = 0
    processed_files = 0

    for file in files:
        processed_files += 1
        if processed_files % 10 == 0 or processed_files == 1 or processed_files == len(files):
            print(
                f"Processing file {processed_files}/{len(files)}: {os.path.basename(file)}")

        try:
            # Read in chunks to keep memory low
            for chunk in pd.read_json(file, lines=True, chunksize=50_000, compression='gzip'):
                if 'start_time' not in chunk.columns:
                    continue

                # Filter date range
                chunk['start_time'] = pd.to_datetime(
                    chunk['start_time'], errors='coerce')
                mask = (chunk['start_time'] >= start_date) & (
                    chunk['start_time'] <= end_date)
                filtered = chunk[mask].copy()

                if not filtered.empty:
                    dfs.append(filtered)
                    total_rows += len(filtered)

                    # Optional: concat every N chunks to avoid too many small dfs in memory
                    if len(dfs) >= 20:
                        df_chunk = pd.concat(dfs, ignore_index=True)
                        dfs = [df_chunk]

        except Exception as e:
            print(f"⚠️  Error processing {file}: {e}")
            continue

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = pd.DataFrame()

    print(f"✅ Extracted {len(df):,} measurements in date range.")

    # ==================== STEP 3: Add metadata and save Parquet ====================
    df["extracted_at"] = datetime.now()

    # Select/rename columns to match your schema (add more if needed)
    columns_to_keep = [
        'measurement_id', 'country', 'asn', 'test_name', 'input',
        'start_time', 'probe_cc', 'probe_asn'
    ]
    # You may need to map actual column names from OONI records
    for col in ['status']:  # Add any derived columns here if required
        if col not in df.columns:
            df[col] = None

    df = df.reindex(columns=columns_to_keep +
                    ['status', 'extracted_at'], fill_value=None)

    df.to_parquet(parquet_out, index=False, compression='snappy')

    print(f"✅ Final Parquet saved with {len(df):,} rows → {parquet_out}")
    return df
