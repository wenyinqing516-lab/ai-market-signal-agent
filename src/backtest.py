"""Event study, not a capital-constrained portfolio simulation."""
import numpy as np
import pandas as pd

def forward_returns(news, price_frame, side, cost_bps=10):
    # Strictly later close, with a processing delay: never trade a known close.
    available = pd.Timestamp(news["available_at"]) + pd.Timedelta(minutes=5)
    ticker = price_frame[price_frame.ticker == news["ticker"]].set_index("session_close").close
    benchmark = price_frame[price_frame.ticker == "SPY"].set_index("session_close").close
    ticker = ticker.sort_index()
    candidates = np.flatnonzero(ticker.index > available)
    rows = []
    for horizon in [1, 5, 20]:
        row = {"id": news["id"], "ticker": news["ticker"], "horizon": horizon,
               "position": side, "status": "no_entry", "entry_at": None, "exit_at": None,
               "forward_return": None, "spy_return": None, "excess_return": None,
               "signed_net_return": None}
        if len(candidates):
            start = int(candidates[0])
            row["entry_at"] = ticker.index[start].isoformat()
            row["status"] = "right_censored"
            if start + horizon < len(ticker):
                end = start + horizon
                entry, exit_ = ticker.index[start], ticker.index[end]
                row["exit_at"] = exit_.isoformat()
                row["forward_return"] = float(ticker.iloc[end] / ticker.iloc[start] - 1)
                if entry in benchmark.index and exit_ in benchmark.index:
                    row["spy_return"] = float(benchmark.loc[exit_] / benchmark.loc[entry] - 1)
                    row["excess_return"] = row["forward_return"] - row["spy_return"]
                row["signed_net_return"] = side * row["forward_return"] - abs(side) * cost_bps / 10000
                row["status"] = "ok"
        rows.append(row)
    return rows

def summarize(rows):
    result = []
    for horizon in [1, 5, 20]:
        all_rows = [r for r in rows if r["horizon"] == horizon]
        valid = [r for r in all_rows if r["status"] == "ok"]
        active = [r for r in valid if r["position"] != 0]
        mean = lambda key, records: float(np.mean([r[key] for r in records])) if records else None
        result.append({"horizon": horizon, "events": len(all_rows), "valid": len(valid),
                       "active": len(active), "censored_or_missing": len(all_rows)-len(valid),
                       "mean_active_net": mean("signed_net_return", active),
                       "always_long_gross": mean("forward_return", valid),
                       "mean_active_excess": mean("excess_return", [r for r in active if r["excess_return"] is not None]),
                       "hit_rate": float(np.mean([r["position"]*r["forward_return"] > 0 for r in active])) if active else None})
    return result
