"""Offline smoke test: verifies the compute + tailoring layers work WITHOUT any
API keys or network. Generates synthetic OHLCV so you can confirm pandas-ta imports
cleanly (the numpy<2 pin matters) and indicators flow through to the tailoring layer.

Run from the backend/ directory:  python -m scripts.smoke_test
"""
import numpy as np
import pandas as pd

from app import backtest, indicators, signals, tailoring, verdict
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

    # --- Verdict engine: deterministic per-horizon read -----------------------
    print("== VERDICT ==")
    # 200 bars: SMA200 exists exactly at the last bar, but 1y-change (needs >252)
    # doesn't — exercises graceful degradation. Also test a long 300-bar frame.
    for n in (200, 300):
        df_v = make_synthetic(n)
        ind_v = indicators.compute_indicators(df_v)
        v = verdict.compute_verdict(df_v, ind_v, signals.detect_signals(df_v))
        assert [h["key"] for h in v["horizons"]] == ["short", "medium", "long"], "horizon keys"
        for h in v["horizons"]:
            assert h["verdict"] in ("favorable", "neutral", "unfavorable", "insufficient"), "verdict bucket"
            assert abs(h["score"]) <= h["max_score"], "score bounds"
            assert h["factors"], "factors present"
            dirs = {f["direction"] for f in h["factors"]}
            assert dirs <= {"bullish", "bearish", "neutral", "unavailable"}, "factor directions"
        print(f"  n={n}: " + "  ".join(
            f"{h['key']}={h['verdict']}({h['score']:+d}/{h['max_score']})" for h in v["horizons"]
        ))
    print()

    # --- Backtester: run every strategy and sanity-check the simulation math ---
    print("== BACKTEST ==")
    for key in backtest.STRATEGIES:
        res = backtest.run_backtest(df, key, initial_cash=10_000)

        # Internal consistency: curves cover every bar; final equity matches the
        # curve; open trades are excluded from the closed-trade count.
        assert len(res["equity_curve"]) == res["bars"] == len(df), "equity curve length"
        assert len(res["benchmark_curve"]) == res["bars"], "benchmark curve length"
        assert res["final_equity"] == res["equity_curve"][-1]["value"], "final equity"
        assert res["num_trades"] == sum(not t["open"] for t in res["trades"]), "trade count"
        assert res["max_drawdown_pct"] <= 0, "drawdown sign"
        assert 0 <= res["exposure_pct"] <= 100, "exposure range"

        print(
            f"  {key:13} trades={res['num_trades']:2}  "
            f"return={res['total_return_pct']:+7.2f}%  "
            f"buy&hold={res['buy_hold_return_pct']:+7.2f}%  "
            f"win={res['win_rate_pct']}  maxDD={res['max_drawdown_pct']:.2f}%  "
            f"exposure={res['exposure_pct']}%"
        )
    print()

    print("OK — compute + tailoring + backtest pipeline works end to end.")


if __name__ == "__main__":
    main()
