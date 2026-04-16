"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - raw_dev
  - dataset_ooni

description: |
  STRICT RAW ingestion of OONI Kenya measurements.

  - Line-by-line JSON parsing (OONI standard)
  - test_keys treated as dynamic dict
  - raw_test_keys preserved for reproducibility
  - Explicit parquet output for GCS / BigQuery

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from typing import Any, Dict
from pathlib import Path
from datetime import datetime
import sys
import gzip
import json


# ---------------------------------------------------------------------------
# ENV IMPORT (CLEAN + SAFE)
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from _env import require_dev, resolve_env  # type: ignore
except Exception:
    def require_dev(x): return None
    def resolve_env(fallback="dev"): return fallback

ENV = resolve_env(fallback="dev")
require_dev(ENV)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
ROOT = Path("data/dev/ooni/ooni-kenya-censorship")
OUT_DIR = Path("data/dev/ooni")
OUT_FILE = OUT_DIR / "ooni_measurements.parquet"

START_DATE = "2023-06-01"
END_DATE = "2025-06-30"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def resolve_time(obj: Dict[str, Any]) -> pd.Timestamp:
    ts = (
        obj.get("measurement_start_time")
        or obj.get("test_start_time")
        or obj.get("started_at")
    )
    return pd.to_datetime(ts, utc=True, errors="coerce")


def safe_bool(x: Any) -> bool:
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ("true", "1", "yes")
    return bool(x)


def safe_int(x: Any) -> int:
    try:
        return int(x or 0)
    except Exception:
        return 0


def extract_row(obj: Dict[str, Any], t: pd.Timestamp) -> Dict[str, Any]:
    test_keys = obj.get("test_keys") or {}

    row = {
        "measurement_id": obj.get("measurement_uid") or obj.get("id"),
        "country": obj.get("probe_cc"),
        "asn": obj.get("asn"),
        "probe_cc": obj.get("probe_cc"),
        "probe_asn": obj.get("probe_asn"),
        "test_name": obj.get("test_name"),
        "input": obj.get("input"),

        "start_time": t,
        "part": t.strftime("%Y-%m-%d"),
        "extracted_at": datetime.utcnow(),

        "raw_test_keys": json.dumps(test_keys, default=str),

        "telegram_http_blocking": safe_bool(test_keys.get("telegram_http_blocking")),
        "telegram_tcp_blocking": safe_bool(test_keys.get("telegram_tcp_blocking")),

        "whatsapp_endpoints_blocked": test_keys.get("endpoints_status") == "blocked",
        "whatsapp_dns_inconsistent": test_keys.get("dns_consistent") is False,
        "whatsapp_web_failure": test_keys.get("web_failure"),

        "signal_backend_failure": test_keys.get("signal_backend_failure"),

        "tor_or_port_accessible": safe_int(test_keys.get("or_port_accessible")),
        "tor_obfs4_accessible": safe_int(test_keys.get("obfs4_accessible")),
        "tor_dir_port_accessible": safe_int(test_keys.get("dir_port_accessible")),

        "psiphon_failure": test_keys.get("failure"),

        "has_failure": obj.get("failure") is not None,
    }

    hashable = {k: v for k, v in row.items() if k not in (
        "extracted_at", "row_hash")}
    row["row_hash"] = hash(json.dumps(hashable, sort_keys=True, default=str))

    return row


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def materialize() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = pd.to_datetime(START_DATE, utc=True)
    end = pd.to_datetime(END_DATE, utc=True)

    files = sorted(ROOT.rglob("*.jsonl.gz"))
    if not files:
        raise FileNotFoundError(f"No files found under {ROOT}")

    rows = []

    for f in files:
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    t = resolve_time(obj)
                    if pd.isna(t) or t < start or t > end:
                        continue

                    if obj.get("probe_cc") != "KE":
                        continue

                    rows.append(extract_row(obj, t))
        except Exception:
            continue

    if not rows:
        raise ValueError("No rows after filtering")

    df = (
        pd.DataFrame(rows)
        .sort_values("start_time")
        .drop_duplicates(subset=["measurement_id"])
        .reset_index(drop=True)
    )

    df.to_parquet(
        OUT_FILE,
        index=False,
        engine="pyarrow",
        compression="snappy"
    )

    print(f"✅ Parquet written → {OUT_FILE} ({len(df):,} rows)")

    return df
