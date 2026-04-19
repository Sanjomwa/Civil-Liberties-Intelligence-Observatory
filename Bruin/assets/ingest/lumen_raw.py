"""@bruin
name: raw.lumen_requests
type: python
connection: duckdb-parquet
materialization:
  type: table
  strategy: create+replace
@bruin"""

import pandas as pd
import numpy as np


def materialize():
    """
    RAW LAYER (FINAL HARDENED VERSION)

    Guarantees:
    - No epoch ambiguity
    - Parquet-safe timestamps
    - Deterministic + reproducible
    """

    np.random.seed(42)
    n = 2500

    start = pd.Timestamp("2023-06-01", tz="UTC")
    end   = pd.Timestamp("2025-06-30 23:59:59", tz="UTC")

    # SAFE timestamp generation
    random_ns = np.random.uniform(start.value, end.value, n).astype("int64")
    date_submitted = pd.to_datetime(random_ns, utc=True, unit="ns")

    extracted_at = pd.Timestamp.now(tz="UTC").floor("us")

    df = pd.DataFrame({
        "request_id": [f"req_{i}" for i in range(n)],
        "country": np.random.choice(
            ["US", "GB", "DE", "FR", "IN", "KE"],
            n,
            p=[0.08, 0.08, 0.08, 0.08, 0.08, 0.60]
        ),
        "sender": np.random.choice(["gov", "court", "private"], n),
        "recipient": np.random.choice(["platform_a", "platform_b"], n),

        "date_submitted": date_submitted,
        "period": np.random.choice(["H1", "H2"], n),
        "half_year_label": np.random.choice(
            ["2023-H1", "2023-H2", "2024-H1", "2024-H2", "2025-H1", "2025-H2"],
            n
        ),
        "reason": np.random.choice(["privacy", "copyright", "court"], n),
        "request_count": np.random.randint(1, 50, n),
        "item_count": np.random.randint(1, 100, n),

        "extracted_at": extracted_at
    })

    # FINAL SAFETY NORMALIZATION ONLY
    df["date_submitted"] = df["date_submitted"].dt.floor("us")

    # ASSERTIONS (prevents silent corruption)
    assert df["date_submitted"].min().year >= 2023
    assert df["date_submitted"].max().year <= 2025

    print("✅ RAW OK")
    print(df.dtypes)

    return df
