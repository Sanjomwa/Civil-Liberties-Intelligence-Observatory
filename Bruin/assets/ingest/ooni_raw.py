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
  STRICT RAW ingestion of OONI Kenya censorship measurements.
  Flattens test_keys into deterministic schema for downstream BigQuery/GCS loads.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: part
    type: STRING
    description: Partition date derived from start_time (YYYY-MM-DD)

  - name: measurement_id
    type: STRING
    description: Unique OONI measurement identifier

  - name: country
    type: STRING
    description: Probe country code

  - name: probe_cc
    type: STRING
    description: Probe country code

  - name: probe_asn
    type: STRING
    description: Probe ASN

  - name: asn
    type: STRING
    description: Target ASN

  - name: test_name
    type: STRING
    description: OONI test type

  - name: input
    type: STRING
    description: Tested URL or endpoint

  - name: start_time
    type: TIMESTAMP
    description: Normalized measurement start time (UTC)

  - name: extracted_at
    type: TIMESTAMP
    description: Ingestion timestamp (UTC)

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
    type: STRING

  # SIGNAL
  - name: signal_backend_failure
    type: STRING

  # TOR
  - name: tor_or_port_accessible
    type: INTEGER
  - name: tor_obfs4_accessible
    type: INTEGER

  # PSIPHON
  - name: psiphon_failure
    type: STRING

  # DERIVED
  - name: is_blocked
    type: BOOLEAN
  - name: is_confirmed_block
    type: BOOLEAN
  - name: has_measurement_failure
    type: BOOLEAN
  - name: blocking_signal_type
    type: STRING
"""

import gzip
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd


# -----------------------------
# SAFE TYPE HELPERS
# -----------------------------
def safe_bool(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "t")
    return False


def safe_int(val: Any) -> int:
    try:
        return int(val or 0)
    except Exception:
        return 0


def safe_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    return str(val)


# -----------------------------
# TIMESTAMP RESOLVER (CRITICAL FIX)
# -----------------------------
def resolve_start_time(obj: Dict[str, Any]) -> Optional[pd.Timestamp]:
    ts = (
        obj.get("measurement_start_time")
        or obj.get("test_start_time")
        or obj.get("started_at")
    )
    return pd.to_datetime(ts, utc=True, errors="coerce")


# -----------------------------
# MAIN INGESTION FUNCTION
# -----------------------------
def materialize(start_date: str, end_date: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start_date, utc=True)
    end_ts = pd.to_datetime(end_date, utc=True)

    root = Path("data/dev/ooni/ooni-kenya-censorship")
    rows: List[Dict[str, Any]] = []

    for path in root.rglob("*.jsonl.gz"):
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue

                    start_time = resolve_start_time(obj)
                    if start_time is None or pd.isna(start_time):
                        continue

                    if start_time < start_ts or start_time > end_ts:
                        continue

                    test_keys = obj.get("test_keys") or {}

                    row: Dict[str, Any] = {
                        # identity
                        "measurement_id": obj.get("measurement_uid"),
                        "country": obj.get("probe_cc"),
                        "probe_cc": obj.get("probe_cc"),
                        "probe_asn": obj.get("probe_asn"),
                        "asn": obj.get("asn"),
                        "test_name": obj.get("test_name"),
                        "input": obj.get("input"),
                        "start_time": start_time,
                        "extracted_at": datetime.utcnow(),

                        # PARTITION COLUMN (CRITICAL FOR BIGQUERY/GCS)
                        "part": start_time.strftime("%Y-%m-%d"),
                    }

                    # -------------------------
                    # TELEGRAM (STRICT RAW)
                    # -------------------------
                    row["telegram_http_blocking"] = safe_bool(
                        test_keys.get("telegram_http_blocking")
                    )
                    row["telegram_tcp_blocking"] = safe_bool(
                        test_keys.get("telegram_tcp_blocking")
                    )

                    # -------------------------
                    # WHATSAPP (STRICT RAW)
                    # -------------------------
                    row["whatsapp_endpoints_blocked"] = (
                        test_keys.get("endpoints_status") == "blocked"
                    )
                    row["whatsapp_endpoints_dns_inconsistent"] = (
                        test_keys.get("dns_consistent") is False
                    )
                    row["whatsapp_web_failure"] = safe_str(
                        test_keys.get("web_failure")
                    )

                    # -------------------------
                    # SIGNAL (STRICT RAW)
                    # -------------------------
                    row["signal_backend_failure"] = safe_str(
                        test_keys.get("signal_backend_failure")
                    )

                    # -------------------------
                    # TOR (STRICT RAW)
                    # -------------------------
                    row["tor_or_port_accessible"] = safe_int(
                        test_keys.get("or_port_accessible")
                    )
                    row["tor_obfs4_accessible"] = safe_int(
                        test_keys.get("obfs4_accessible")
                    )

                    # -------------------------
                    # PSIPHON
                    # -------------------------
                    row["psiphon_failure"] = safe_str(
                        test_keys.get("failure")
                    )

                    # -------------------------
                    # DERIVED (MINIMAL RAW LOGIC)
                    # -------------------------
                    row["has_measurement_failure"] = obj.get("failure") is not None

                    row["is_confirmed_block"] = (
                        row["telegram_http_blocking"]
                        or row["telegram_tcp_blocking"]
                        or row["whatsapp_endpoints_blocked"]
                    )

                    row["is_blocked"] = (
                        row["is_confirmed_block"]
                        or row["has_measurement_failure"]
                    )

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
            # RAW LAYER RULE: skip corrupted files but never fail pipeline
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # deterministic ordering
    df = df.sort_values("start_time")

    # stable deduplication
    df = df.drop_duplicates(subset=["measurement_id"])

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

  df.to_parquet(
        OUTPUT_FILE,
        index=False,
        engine="pyarrow",
        compression="snappy"
    )

return df
