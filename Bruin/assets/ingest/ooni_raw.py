"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.11
connection: duckdb-parquet
description: |
  Fast daily sync of ONLY Kenya (KE) OONI data from 2023-06-01 to 2025-06-30.
  Filters to censorship-relevant tests: web_connectivity, messaging apps, circumvention tools.

materialization:
  type: table
  strategy: create+replace

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
    description: OONI Probe test type
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

import subprocess
import glob
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


def materialize():
    base_path = "/workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin/data/dev/ooni"
    parquet_out = f"{base_path}/ooni_measurements.parquet"

    Path(base_path).mkdir(parents=True, exist_ok=True)

    # Auto-install AWS CLI if missing
    try:
        subprocess.run(["aws", "--version"], check=True,
                       capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("🔧 Installing AWS CLI...")
        install_cmd = """
        cd /tmp && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
        unzip -q awscliv2.zip && sudo ./aws/install && rm -rf awscliv2.zip aws
        """
        subprocess.run(install_cmd, shell=True,
                       check=True, executable="/bin/bash")
        print("✅ AWS CLI installed.")

    # ==================== Filtered Daily Sync ====================
    files_already_present = glob.glob(
        f"{base_path}/**/*.jsonl.gz", recursive=True)

    if len(files_already_present) > 300:
        print(
            f"✅ Skipping download — {len(files_already_present)} files already present.")
    else:
        print("🚀 Starting FAST filtered daily sync for Kenya censorship data...")
        print("   Test types: web_connectivity, whatsapp, telegram, facebook_messenger, signal, tor, psiphon, dnscheck")

        relevant_tests = ["web_connectivity", "whatsapp", "telegram", "facebook_messenger",
                          "signal", "tor", "psiphon", "dnscheck"]

        start_date = datetime(2023, 6, 1)
        end_date = datetime(2025, 6, 30)
        current = start_date

        while current <= end_date:
            date_str = current.strftime("%Y%m%d")
            print(f"   → Syncing {date_str} ...")

            for test in relevant_tests:
                sync_cmd = [
                    "aws", "s3", "--no-sign-request", "sync",
                    f"s3://ooni-data-eu-fra/raw/{date_str}/", base_path,
                    "--exclude", "*",
                    f"--include", f"*/KE/{test}/*.jsonl.gz"
                ]
                try:
                    subprocess.run(sync_cmd, check=True,
                                   capture_output=True, text=True, timeout=180)
                except:
                    pass  # Many day/test combos have no data

            current += timedelta(days=1)

        print("✅ Filtered daily sync completed.")

    # ==================== Process files ====================
    print("📂 Finding downloaded .jsonl.gz files...")
    files = sorted(glob.glob(f"{base_path}/**/*.jsonl.gz", recursive=True))
    print(f"Found {len(files)} files (filtered to relevant tests).")

    if not files:
        raise FileNotFoundError(
            "No files downloaded. Check connection and retry.")

    start_ts = pd.Timestamp("2023-06-01")
    end_ts = pd.Timestamp("2025-06-30")

    dfs = []
    for i, fpath in enumerate(files, 1):
        if i % 20 == 0 or i == 1 or i == len(files):
            print(f"Processing {i}/{len(files)}: {os.path.basename(fpath)}")

        try:
            for chunk in pd.read_json(fpath, lines=True, chunksize=100_000, compression="gzip"):
                if "start_time" not in chunk.columns:
                    continue
                chunk["start_time"] = pd.to_datetime(
                    chunk["start_time"], errors="coerce")
                mask = (chunk["start_time"] >= start_ts) & (
                    chunk["start_time"] <= end_ts)
                filtered = chunk[mask].copy()
                if not filtered.empty:
                    dfs.append(filtered)
        except Exception as e:
            print(f"⚠️ Error processing {os.path.basename(fpath)}: {e}")
            continue

    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    print(f"✅ Loaded {len(df):,} relevant measurements.")

    df["extracted_at"] = datetime.now()

    keep_cols = ["measurement_id", "country", "asn", "test_name", "input",
                 "start_time", "probe_cc", "probe_asn"]
    for col in ["status"]:
        if col not in df.columns:
            df[col] = pd.NA

    df = df.reindex(columns=keep_cols +
                    ["status", "extracted_at"], fill_value=None)

    df.to_parquet(parquet_out, index=False, compression="snappy")
    print(f"✅ Parquet saved: {len(df):,} rows → {parquet_out}")
    return df
