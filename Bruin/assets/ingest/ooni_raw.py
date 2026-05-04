"""@bruin
name: raw.ooni_conflict_measurements
type: python
image: python:3.12
connection: duckdb-parquet

tags:
  - raw_dev
  - dataset_ooni

description: |
  Lands raw OONI measurements as reprocessable Parquet.
  This asset preserves raw test_keys and raw measurement JSON. It does not
  derive final censorship flags during ingestion.

materialization:
  type: table
  strategy: create+replace
@bruin"""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
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

CHUNK_SIZE = 10_000   # LOWERED

PROBE_CC = "KE"


SCHEMA = pa.schema(
    [
        ("measurement_id", pa.string()),
        ("report_id", pa.string()),
        ("input", pa.string()),
        ("probe_cc", pa.string()),
        ("probe_asn", pa.int64()),
        ("probe_network_name", pa.string()),
        ("test_name", pa.string()),
        ("test_version", pa.string()),
        ("measurement_start_time", pa.timestamp("us", tz="UTC")),
        ("test_start_time", pa.timestamp("us", tz="UTC")),
        ("measurement_date", pa.date32()),
        ("failure", pa.string()),
        ("raw_test_keys", pa.string()),
        ("raw_measurement", pa.string()),
        ("source_file", pa.string()),
        ("extracted_at", pa.timestamp("us", tz="UTC")),
    ]
)


def parse_time(value: Any) -> pd.Timestamp:
    return pd.to_datetime(value, utc=True, errors="coerce")


def safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(str(value).replace("AS", "").strip())
    except (TypeError, ValueError):
        return None


def measurement_time(obj: dict[str, Any]) -> pd.Timestamp:
    return parse_time(
        obj.get("measurement_start_time")
        or obj.get("test_start_time")
        or obj.get("started_at")
    )


def extract_row(obj: dict[str, Any], source_file: Path) -> dict[str, Any] | None:
    ts = measurement_time(obj)
    if pd.isna(ts):
        return None

    if obj.get("probe_cc") != PROBE_CC:
        return None

    test_start_time = parse_time(obj.get("test_start_time"))
    test_keys = obj.get("test_keys") or {}

    return {
        "measurement_id": obj.get("measurement_uid") or obj.get("id"),
        "report_id": obj.get("report_id"),
        "input": obj.get("input"),
        "probe_cc": obj.get("probe_cc"),
        "probe_asn": safe_int(obj.get("probe_asn") or obj.get("asn")),
        "probe_network_name": obj.get("probe_network_name"),
        "test_name": obj.get("test_name"),
        "test_version": obj.get("test_version"),
        "measurement_start_time": ts.to_pydatetime(),
        "test_start_time": None
        if pd.isna(test_start_time)
        else test_start_time.to_pydatetime(),
        "measurement_date": ts.date(),
        "failure": obj.get("failure"),
        "raw_test_keys": json.dumps(test_keys, default=str, separators=(",", ":")),
        "raw_measurement": json.dumps(obj, default=str, separators=(",", ":")),
        "source_file": str(source_file.relative_to(ROOT))
        if source_file.is_relative_to(ROOT)
        else str(source_file),
        "extracted_at": datetime.now(timezone.utc),
    }


def write_chunk(writer: pq.ParquetWriter | None, rows: list[dict[str, Any]]) -> pq.ParquetWriter:
    frame = pd.DataFrame(rows)
    table = pa.Table.from_pandas(frame, schema=SCHEMA, preserve_index=False)

    if writer is None:
        writer = pq.ParquetWriter(
            OUT_FILE,
            SCHEMA,
            compression="snappy",
            use_dictionary=True,
            write_statistics=True,
        )

    writer.write_table(table)
    return writer


def materialize() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_FILE.exists():
        OUT_FILE.unlink()
