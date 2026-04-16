"""
@bruin
tags:
  - raw_dev
  - dataset_ooni_conflict_measurements
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet
description: |
  Raw ingestion of OONI Kenya censorship measurements.
  Flattens test_keys and normalizes blocking signals into a unified schema.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: VARCHAR
  - name: country
    type: VARCHAR
  - name: asn
    type: VARCHAR
  - name: test_name
    type: VARCHAR
  - name: input
    type: VARCHAR
  - name: start_time
    type: TIMESTAMP
  - name: probe_cc
    type: VARCHAR
  - name: probe_asn
    type: VARCHAR
  - name: extracted_at
    type: TIMESTAMP

  # TELEGRAM
  - name: telegram_http_blocking
    type: BOOLEAN
  - name: telegram_tcp_blocking
    type: BOOLEAN

  # WHATSAPP
  - name: whatsapp_endpoints_blocked
    type: BOOLEAN
  - name: whatsapp_endpoints_dns_inconsistent
    type: BOOLEAN
  - name: whatsapp_web_failure
    type: VARCHAR

  # SIGNAL
  - name: signal_backend_failure
    type: VARCHAR

  # TOR
  - name: tor_or_port_accessible
    type: INTEGER
  - name: tor_obfs4_accessible
    type: INTEGER

  # PSIPHON
  - name: psiphon_failure
    type: VARCHAR

  # DERIVED
  - name: is_blocked
    type: BOOLEAN
  - name: is_confirmed_block
    type: BOOLEAN
  - name: has_measurement_failure
    type: BOOLEAN
  - name: blocking_signal_type
    type: VARCHAR
@bruin
"""

import os
import json
import gzip
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


# -------------------------
# BRUIN CONTRACT FIX
# -------------------------
def materialize(start_date: str, end_date: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start_date, utc=True)
    end_ts = pd.to_datetime(end_date, utc=True)

    root = "data/dev/ooni/ooni-kenya-censorship"

    rows: List[Dict[str, Any]] = []

    for path in Path(root).rglob("*.jsonl.gz"):
        try:
            with gzip.open(path, "rt") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue

                    ts = pd.to_datetime(obj.get("measurement_start_time"), utc=True, errors="coerce")
                    if pd.isna(ts) or ts < start_ts or ts > end_ts:
                        continue

                    test_keys = obj.get("test_keys", {}) or {}
                    test_name = obj.get("test_name")

                    row = {
                        "measurement_id": obj.get("measurement_uid"),
                        "country": obj.get("probe_cc"),
                        "asn": obj.get("asn"),
                        "test_name": test_name,
                        "input": obj.get("input"),
                        "start_time": ts,
                        "probe_cc": obj.get("probe_cc"),
                        "probe_asn": obj.get("probe_asn"),
                        "extracted_at": datetime.utcnow(),
                    }

                    # -------------------------
                    # TELEGRAM
                    # -------------------------
                    row["telegram_http_blocking"] = bool(test_keys.get("telegram_http_blocking"))
                    row["telegram_tcp_blocking"] = bool(test_keys.get("telegram_tcp_blocking"))

                    # -------------------------
                    # WHATSAPP
                    # -------------------------
                    row["whatsapp_endpoints_blocked"] = bool(
                        test_keys.get("endpoints_status") == "blocked"
                    )
                    row["whatsapp_endpoints_dns_inconsistent"] = bool(
                        test_keys.get("dns_consistent") is False
                    )
                    row["whatsapp_web_failure"] = test_keys.get("web_failure")

                    # -------------------------
                    # SIGNAL
                    # -------------------------
                    row["signal_backend_failure"] = test_keys.get("signal_backend_failure")

                    # -------------------------
                    # TOR
                    # -------------------------
                    row["tor_or_port_accessible"] = int(
                        test_keys.get("or_port_accessible", 0) or 0
                    )
                    row["tor_obfs4_accessible"] = int(
                        test_keys.get("obfs4_accessible", 0) or 0
                    )

                    # -------------------------
                    # PSIPHON
                    # -------------------------
                    row["psiphon_failure"] = test_keys.get("failure")

                    # -------------------------
                    # DERIVED SIGNALS
                    # -------------------------
                    row["has_measurement_failure"] = obj.get("failure") is not None

                    row["is_confirmed_block"] = (
                        row["telegram_http_blocking"]
                        or row["telegram_tcp_blocking"]
                        or row["whatsapp_endpoints_blocked"]
                    )

                    row["is_blocked"] = row["is_confirmed_block"] or row["has_measurement_failure"]

                    if row["telegram_http_blocking"] or row["telegram_tcp_blocking"]:
                        row["blocking_signal_type"] = "telegram"
                    elif row["whatsapp_endpoints_blocked"]:
                        row["blocking_signal_type"] = "whatsapp"
                    elif row["signal_backend_failure"]:
                        row["blocking_signal_type"] = "signal"
                    elif row["psiphon_failure"]:
                        row["blocking_signal_type"] = "psiphon"
                    else:
                        row["blocking_signal_type"] = None

                    rows.append(row)

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values("start_time")

    return df
