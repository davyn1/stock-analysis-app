"""Offline smoke test: verifies the compute + tailoring layers work WITHOUT any
API keys or network. Generates synthetic OHLCV so you can confirm pandas-ta imports
cleanly (the numpy<2 pin matters) and indicators flow through to the tailoring layer.

Run from the backend/ directory:  python -m scripts.smoke_test
"""
import numpy as np
import pandas as pd

from app import indicators, tailoring
from app.schemas import ExperienceLevel


def make_synthetic(n=200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=pd.Timestamp.now("UTC").normalize(), periods=n, freq="D")
    # Random walk for a believable price series.
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    open_ = close + rng.normal(0, 1, n)
    volume = rng.uniform(1e6, 5e6, n)
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
    df.index.name = "date"
    return df


def main():
    df = make_synthetic()
    all_ind = indicators.compute_indicators(df)
    print(f"Computed {len(all_ind)} indicator values.\n")

    for level in ExperienceLevel:
        surfaced = tailoring.filter_indicators(all_ind, level)
        print(f"== {level.value.upper()} ({len(surfaced)} surfaced) ==")
        for k, v in surfaced.items():
            print(f"  {k:16} {v}")
        print()

    print("OK — compute + tailoring pipeline works end to end.")


if __name__ == "__main__":
    main()
