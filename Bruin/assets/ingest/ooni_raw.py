"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - raw_dev
  - dataset_ooni

materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
from typing import Any, Dict, List
from pathlib import Path
from datetime import datetime
import gzip
import json
import pyarrow as pa
import pyarrow.parquet as pq


# ---------------------------------------------------------------------------
# PATH FIX
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]

ROOT = PROJECT_ROOT / "data/dev/ooni/ooni-kenya-censorship"
OUT_DIR = PROJECT_ROOT / "data/dev/ooni"
OUT_FILE = OUT_DIR / "ooni_measurements.parquet"

START_DATE = "2023-06-01"
END_DATE = "2025-06-30"

CHUNK_SIZE = 10_000   # 🔥 LOWERED


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


def safe_bool(x):
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ("true", "1", "yes")
    return bool(x)


def safe_int(x):
    try:
        return int(x or 0)
    except:
        return 0


def extract_row(obj, t):
    tk = obj.get("test_keys") or {}

    return {
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

        "raw_test_keys": json.dumps(tk, default=str),

        "telegram_http_blocking": safe_bool(tk.get("telegram_http_blocking")),
        "telegram_tcp_blocking": safe_bool(tk.get("telegram_tcp_blocking")),

        "whatsapp_endpoints_blocked": tk.get("endpoints_status") == "blocked",
        "whatsapp_dns_inconsistent": tk.get("dns_consistent") is False,
        "whatsapp_web_failure": tk.get("web_failure"),

        "signal_backend_failure": tk.get("signal_backend_failure"),

        "tor_or_port_accessible": safe_int(tk.get("or_port_accessible")),
        "tor_obfs4_accessible": safe_int(tk.get("obfs4_accessible")),
        "tor_dir_port_accessible": safe_int(tk.get("dir_port_accessible")),

        "psiphon_failure": tk.get("failure"),

        "has_failure": obj.get("failure") is not None,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def materialize() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = pd.to_datetime(START_DATE, utc=True)
    end = pd.to_datetime(END_DATE, utc=True)

    files = sorted(ROOT.rglob("*.jsonl.gz"))
    print(f"Found {len(files)} files")

    writer = None
    buffer: List[Dict[str, Any]] = []
    total_rows = 0

    for i, f in enumerate(files, 1):
        if i % 1000 == 0:
            print(f"Processing {i}/{len(files)} | rows: {total_rows}")

        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except:
                        continue

                    t = resolve_time(obj)
                    if pd.isna(t) or t < start or t > end:
                        continue

                    if obj.get("probe_cc") != "KE":
                        continue

                    buffer.append(extract_row(obj, t))

                    if len(buffer) >= CHUNK_SIZE:
                        df_chunk = pd.DataFrame(buffer)
                        table = pa.Table.from_pandas(df_chunk)

                        if writer is None:
                            writer = pq.ParquetWriter(
                                OUT_FILE,
                                table.schema,
                                compression="snappy",
                                use_dictionary=True,
                                write_statistics=False,
                            )

                        writer.write_table(table)

                        total_rows += len(buffer)
                        buffer.clear()

        except Exception:
            continue

    if buffer:
        df_chunk = pd.DataFrame(buffer)
        table = pa.Table.from_pandas(df_chunk)

        if writer is None:
            writer = pq.ParquetWriter(OUT_FILE, table.schema)

        writer.write_table(table)
        total_rows += len(buffer)

    if writer:
        writer.close()

    print(f"✅ Finished. Total rows: {total_rows:,}")

    # 🔥 DO NOT LOAD FILE AGAIN
    return pd.DataFrame()
