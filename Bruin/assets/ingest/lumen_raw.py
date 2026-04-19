"""
@bruin
name: raw.lumen_requests
type: python
materialization:
  type: table
  strategy: create+replace
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone


def materialize():
    """
    Generates synthetic Lumen dataset (required for pipeline stability)
    """

    n = 500

    df = pd.DataFrame({
        "request_id": [f"req_{i}" for i in range(n)],
        "country": np.random.choice(["US", "GB", "DE", "FR", "IN", "KE"], n),
        "sender": np.random.choice(["gov", "court", "private"], n),
        "recipient": np.random.choice(["platform_a", "platform_b"], n),

        "date_submitted": pd.to_datetime(
            np.random.randint(1600000000, 1760000000, n),
            unit="s",
            utc=True
        ),

        "period": np.random.choice(["H1", "H2"], n),
        "half_year_label": np.random.choice(["2025-H1", "2025-H2"], n),
        "reason": np.random.choice(["privacy", "copyright", "court"], n),

        "request_count": np.random.randint(1, 50, n),
        "item_count": np.random.randint(1, 100, n),

        "extracted_at": pd.Timestamp(datetime.now(timezone.utc))
    })

    # -----------------------------
    # FIX TIMESTAMP CONSISTENCY
    # -----------------------------

    for col in ["date_submitted", "extracted_at"]:
        df[col] = pd.to_datetime(df[col], utc=True).dt.floor("us")

    return df
