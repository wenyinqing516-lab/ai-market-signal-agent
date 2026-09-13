# Data provenance and import contract

Bundled data is **entirely synthetic**; ticker names are illustrative. Prices use
a seeded common-factor process (seed 20260913) and are independent of news labels.
There are 180 weekday observations per asset. This is NOT a real exchange calendar:
holidays, early closes, and daylight saving time are intentionally not modeled.
No performance result from these samples is investment evidence.

Price CSV: `session_close,ticker,close`. Use timezone-aware timestamps and
consistently adjusted prices (splits and dividends), document vendor, adjustment
method, retrieval date and license. All assets must share the intended session
calendar. Never mix adjusted closes with unadjusted prices.
The pipeline reads user-supplied CSV files; it does not claim a live data feed.

Real-data upgrade: export licensed historical prices to this schema, preserve the
original raw files and provenance manifest, inspect missing sessions/corporate
actions, then pass the file with `--prices`. Check the source's redistribution
rights before placing real datasets in a public repository.
