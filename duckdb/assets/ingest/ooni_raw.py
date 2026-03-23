"""@bruin
name: raw.ooni_raw_s3
type: python
image: python:3.11
connection: duckdb-default
description: |
  Ingests OONI censorship measurement data from the public OONI S3 bucket.
  Fetches JSONL measurement results filtered by country and test type.
  Returns a Pandas DataFrame for Bruin to append into DuckDB.

materialization:
  type: table
  strategy: append

columns:
  - name: measurement_id
    type: VARCHAR
    description: Unique OONI measurement ID
  - name: country
    type: VARCHAR
    description: Country code (ISO two-letter)
  - name: asn
    type: INTEGER
    description: Autonomous System Number (network identifier)
  - name: test_name
    type: VARCHAR
    description: OONI Probe test type (e.g. web_connectivity, whatsapp)
  - name: input
    type: VARCHAR
    description: Domain or URL tested
  - name: start_time
    type: TIMESTAMP
    description: Measurement start time (UTC)
  - name: status
    type: VARCHAR
    description: Result status (ok, anomaly, confirmed, failure)
  - name: probe_cc
    type: VARCHAR
    description: Country code of probe
  - name: probe_asn
    type: INTEGER
    description: ASN of probe
  - name: extracted_at
    type: TIMESTAMP
    description: Timestamp when ingested
@bruin"""

import pandas as pd
import gzip, json, os
from datetime import datetime
import boto3

def materialize():
    # Environment variables for filters
    bruin_vars = os.environ.get("BRUIN_VARS")
    filters = {}
    if bruin_vars:
        import json as js
        filters = js.loads(bruin_vars)

    country = filters.get("country", "KE")  # default Kenya
    test_name = filters.get("test_name", "webconnectivity")
    date_prefix = filters.get("date_prefix", "20240301")  # YYYYMMDD

    # Connect to OONI public S3 bucket (no credentials needed)
    s3 = boto3.client("s3", config=boto3.session.Config(signature_version="unsigned"))
    bucket = "ooni-data-eu-fra"

    # Example path: raw/YYYYMMDD/HH/CC/testname/*.jsonl.gz
    prefix = f"raw/{date_prefix}/"
    objs = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    rows = []
    for obj in objs.get("Contents", []):
        key = obj["Key"]
        if country in key and test_name in key:
            print(f"Fetching {key}")
            body = s3.get_object(Bucket=bucket, Key=key)["Body"]
            with gzip.open(body, "rt") as f:
                for line in f:
                    rows.append(json.loads(line))

    df = pd.DataFrame(rows)
    df["extracted_at"] = datetime.now()

    print(f"Rows ingested: {len(df)}")
    return df
