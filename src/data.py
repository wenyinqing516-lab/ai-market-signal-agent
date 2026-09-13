"""CSV is the provider boundary: preserve point-in-time timestamps and price provenance."""
import numpy as np
import pandas as pd

def prices(path):
    frame = pd.read_csv(path)
    required = {"session_close", "ticker", "close"}
    if not required <= set(frame):
        raise ValueError(f"Prices require {required}")
    # Reject naive times, rather than silently treating local market time as UTC.
    parsed = [pd.Timestamp(x) for x in frame.session_close]
    if any(x.tzinfo is None for x in parsed):
        raise ValueError("session_close must include a timezone")
    frame["session_close"] = pd.to_datetime(frame.session_close, utc=True)
    if frame.duplicated(["session_close", "ticker"]).any():
        raise ValueError("Duplicate ticker/session prices")
    if not np.isfinite(frame.close).all() or (frame.close <= 0).any():
        raise ValueError("Prices must be positive and finite")
    return frame.sort_values(["ticker", "session_close"])

def price_matrix(path):
    return prices(path).pivot(index="session_close", columns="ticker", values="close").sort_index()
