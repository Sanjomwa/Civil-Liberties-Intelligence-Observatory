from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


# ---------------------------------------------------------------------------
# DEFAULT CONFIG
# ---------------------------------------------------------------------------
DEFAULT_ROOT = Path(r"C:\ooni-kenya-censorship")
DEFAULT_OUT_DIR = DEFAULT_ROOT / "processed"
DEFAULT_FINAL_OUT = DEFAULT_OUT_DIR / "ooni_measurements.parquet"

DEFAULT_START_DATE = "2023-06-01"
DEFAULT_END_DATE = "2025-06-30"
DEFAULT_PROBE_CC = "KE"

NUM_WORKERS = max(2, (os.cpu_count() or 4) - 2)
DEFAULT_ROW_CHUNK_SIZE = 2_000


# ---------------------------------------------------------------------------
# HARD SCHEMA CONTRACT
# Matches Bruin/assets/ingest/ooni_raw.py
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def parse_time(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def measurement_time(obj: dict[str, Any]) -> datetime | None:
    return parse_time(
        obj.get("measurement_start_time")
        or obj.get("test_start_time")
        or obj.get("started_at")
    )


def safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(str(value).replace("AS", "").strip())
    except (TypeError, ValueError):
        return None


def relative_source_path(file_path: Path, root: Path) -> str:
    try:
        return str(file_path.relative_to(root))
    except ValueError:
        return str(file_path)


def stable_measurement_id(obj: dict[str, Any], file_path: Path, root: Path) -> str:
    source = relative_source_path(file_path, root)
    existing_id = obj.get("measurement_uid") or obj.get("id")
    if existing_id:
        return str(existing_id)

    identity = {
        "source_file": source,
        "report_id": obj.get("report_id"),
        "input": obj.get("input"),
        "probe_cc": obj.get("probe_cc"),
        "probe_asn": obj.get("probe_asn") or obj.get("asn"),
        "test_name": obj.get("test_name"),
        "test_start_time": obj.get("test_start_time"),
        "measurement_start_time": obj.get("measurement_start_time"),
        "raw": obj,
    }
    payload = json.dumps(identity, default=str,
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_row(
    obj: dict[str, Any],
    file_path: Path,
    root: Path,
    probe_cc: str,
) -> dict[str, Any] | None:
    t = measurement_time(obj)
    if t is None:
        return None

    if obj.get("probe_cc") != probe_cc:
        return None

    test_start_time = parse_time(obj.get("test_start_time"))
    test_keys = obj.get("test_keys") or {}

    return {
        "measurement_id": stable_measurement_id(obj, file_path, root),
        "report_id": obj.get("report_id"),
        "input": obj.get("input"),
        "probe_cc": obj.get("probe_cc"),
        "probe_asn": safe_int(obj.get("probe_asn") or obj.get("asn")),
        "probe_network_name": obj.get("probe_network_name"),
        "test_name": obj.get("test_name"),
        "test_version": obj.get("test_version"),
        "measurement_start_time": t,
        "test_start_time": test_start_time,
        "measurement_date": t.date(),
        "failure": obj.get("failure"),
        "raw_test_keys": json.dumps(test_keys, default=str, separators=(",", ":")),
        "raw_measurement": json.dumps(obj, default=str, separators=(",", ":")),
        "source_file": relative_source_path(file_path, root),
        "extracted_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# WORKER
# ---------------------------------------------------------------------------
def process_batch(
    files: list[Path],
    batch_id: int,
    root: Path,
    shard_dir: Path,
    start_at: datetime,
    end_at: datetime,
    probe_cc: str,
    row_chunk_size: int,
) -> str | None:
    rows: list[dict[str, Any]] = []
    writer: pq.ParquetWriter | None = None
    row_count = 0
    shard_path = shard_dir / f"shard_{batch_id:05d}.parquet"

    for file_path in files:
        try:
            with gzip.open(file_path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    t = measurement_time(obj)
                    if t is None or t < start_at or t > end_at:
                        continue

                    row = extract_row(obj, file_path, root, probe_cc)
                    if row is not None:
                        rows.append(row)

                    if len(rows) >= row_chunk_size:
                        table = pa.Table.from_pylist(rows, schema=SCHEMA)
                        if writer is None:
                            writer = pq.ParquetWriter(
                                shard_path,
                                SCHEMA,
                                compression="snappy",
                                use_dictionary=True,
                                write_statistics=True,
                            )
                        writer.write_table(table)
                        row_count += table.num_rows
                        rows.clear()
        except OSError:
            continue

    if rows:
        table = pa.Table.from_pylist(rows, schema=SCHEMA)
        if writer is None:
            writer = pq.ParquetWriter(
                shard_path,
                SCHEMA,
                compression="snappy",
                use_dictionary=True,
                write_statistics=True,
            )
        writer.write_table(table)
        row_count += table.num_rows
        rows.clear()

    if writer is not None:
        writer.close()

    if row_count == 0:
        return None

    print(f"shard {batch_id:05d}: {row_count:,} rows")
    return str(shard_path)


# ---------------------------------------------------------------------------
# FINAL MERGE
# ---------------------------------------------------------------------------
def merge_final(shards: list[str], final_out: Path, batch_size: int) -> int:
    writer: pq.ParquetWriter | None = None
    total_rows = 0

    for shard in sorted(shards):
        parquet_file = pq.ParquetFile(shard)

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            table = pa.Table.from_batches([batch], schema=SCHEMA)

            if writer is None:
                writer = pq.ParquetWriter(
                    final_out,
                    SCHEMA,
                    compression="snappy",
                    use_dictionary=True,
                    write_statistics=True,
                )

            writer.write_table(table)
            total_rows += table.num_rows

    if writer is not None:
        writer.close()

    return total_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build canonical OONI measurement Parquet locally."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out-file", type=Path, default=DEFAULT_FINAL_OUT)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--probe-cc", default=DEFAULT_PROBE_CC)
    parser.add_argument("--workers", type=int, default=NUM_WORKERS)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument(
        "--row-chunk-size",
        type=int,
        default=DEFAULT_ROW_CHUNK_SIZE,
        help="Rows to buffer before writing each Parquet row group.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete old shard parquet files before processing.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    root = args.root.resolve()
    final_out = args.out_file.resolve()
    out_dir = final_out.parent
    shard_dir = out_dir / "_shards"

    start_at = parse_time(args.start_date)
    end_at = parse_time(args.end_date)
    if start_at is None or end_at is None:
        raise ValueError("Invalid --start-date or --end-date")

    end_at = end_at.replace(hour=23, minute=59, second=59, microsecond=999999)
    probe_cc = args.probe_cc.upper()

    out_dir.mkdir(parents=True, exist_ok=True)
    shard_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        for shard in shard_dir.glob("shard_*.parquet"):
            shard.unlink()

    files = sorted(root.rglob("*.jsonl.gz"))
    if not files:
        raise FileNotFoundError(f"No .jsonl.gz files found under {root}")

    workers = max(1, args.workers)
    batch_size = args.batch_size or max(100, len(files) // (workers * 10) or 1)
    batches = [files[i: i + batch_size]
               for i in range(0, len(files), batch_size)]

    print("Local OONI ingest")
    print(f"root: {root}")
    print(f"out: {final_out}")
    print(f"probe_cc: {probe_cc}")
    print(f"date range: {args.start_date} to {args.end_date}")
    print(f"files: {len(files):,}")
    print(f"workers: {workers}")
    print(f"batches: {len(batches):,}")
    print(f"row chunk size: {args.row_chunk_size:,}")

    shards: list[str] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                process_batch,
                batch,
                batch_id,
                root,
                shard_dir,
                start_at,
                end_at,
                probe_cc,
                args.row_chunk_size,
            )
            for batch_id, batch in enumerate(batches)
        ]

        for future in as_completed(futures):
            shard = future.result()
            if shard:
                shards.append(shard)

    if not shards:
        raise RuntimeError(
            "No rows were extracted. Check root, date range, and probe_cc.")

    if final_out.exists():
        final_out.unlink()

    total_rows = merge_final(shards, final_out, args.row_chunk_size)

    print("")
    print(f"final parquet: {final_out}")
    print(f"rows: {total_rows:,}")
    print(f"shards: {len(shards):,}")


if __name__ == "__main__":
    main()
