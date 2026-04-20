# scripts/generate_lumen_parquet.py

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import os


OUTPUT_PATH = "./lumen_requests.parquet"


def generate():
    np.random.seed(42)
    n = 5000

    start = pd.Timestamp("2023-06-01", tz="UTC")
    end = pd.Timestamp("2025-06-30 23:59:59", tz="UTC")

    # SAFE timestamp generation (no epoch integers)
    random_ns = np.random.uniform(start.value, end.value, n).astype("int64")
    date_submitted = pd.to_datetime(random_ns, unit="ns", utc=True)

    df = pd.DataFrame({
        "request_id": [f"LUMEN-{i:05d}" for i in range(n)],
        "country": np.random.choice(
            ["US", "GB", "DE", "FR", "IN", "KE"],
            n,
            p=[0.05, 0.05, 0.05, 0.05, 0.05, 0.75]
        ),
        "sender": np.random.choice(
            ["Gov Agency", "Court", "Law Firm"], n
        ),
        "recipient": np.random.choice(
            ["Facebook", "Twitter", "YouTube"], n
        ),
        "date_submitted": date_submitted,
        "period": np.random.choice(
            ["2023-06", "2023-12", "2024-06", "2024-12", "2025-06"], n
        ),
        "half_year_label": np.random.choice(
            ["Jan-Jun 2023", "Jul-Dec 2023", "Jan-Jun 2024",
                "Jul-Dec 2024", "Jan-Jun 2025"], n
        ),
        "reason": np.random.choice(
            ["Defamation", "Copyright", "National Security", "Privacy"], n
        ),
        "request_count": np.random.randint(1, 50, n),
        "item_count": np.random.randint(1, 100, n),
        "extracted_at": pd.Timestamp.now(tz="UTC")
    })

    # enforce microsecond precision (BQ safe)
    for col in ["date_submitted", "extracted_at"]:
        df[col] = df[col].dt.floor("us")

    # HARD VALIDATION
    assert df["date_submitted"].min().year >= 2023
    assert df["date_submitted"].max().year <= 2025

    print("✅ Generated dataset")
    print("Rows:", len(df))
    print("Date range:", df["date_submitted"].min(),
          "→", df["date_submitted"].max())
    print(df.dtypes)

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False, engine="pyarrow")

    print(f"✅ Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
