# Three-minute demonstration

1. Open the README and say what the system measures; identify offline/synthetic mode.
2. Run `python demo/run_demo.py`. No network is needed.
3. Open one input and its corresponding output, tracing the values through the code.
4. Show one failing/ambiguous case rather than only successful examples.
5. Explain the next real-data experiment without implying it already happened.


Suggested files: `data/sample/news.jsonl` → `runs/demo/v2/signals.json` →
`runs/demo/v2/forward_returns.json` → `runs/demo/comparison.json`.
Show n012 for mixed earnings/guidance and n024 for a resolved delay that the
keyword baseline misreads. Show the censored 20-session result near the dataset end.
Explain why the v1/v2 offline comparison is a rule comparison, not an LLM finding.
