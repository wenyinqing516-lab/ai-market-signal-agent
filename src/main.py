import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import pandas as pd
from .data import prices
from .signals import Signal, direction, position, offline_classifier
from .llm import structured_call, dump, configure_logging
from .backtest import forward_returns, summarize
from .evaluate import classification_metrics

def load_news(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    seen, unique, validated = set(), [], []
    ids = set()
    for row in rows:
        if not {"id", "ticker", "text", "published_at", "available_at", "source"} <= row.keys():
            raise ValueError("Missing news fields")
        if row["id"] in ids:
            raise ValueError("Duplicate news id")
        ids.add(row["id"])
        for key in ["published_at", "available_at"]:
            if pd.Timestamp(row[key]).tzinfo is None:
                raise ValueError("News timestamps must include timezone")
        if pd.Timestamp(row["available_at"]) < pd.Timestamp(row["published_at"]):
            raise ValueError("available_at precedes publication")
        normalized = " ".join(row["text"].split())
        if not normalized or len(normalized) > 20000:
            raise ValueError("News text empty or over 20000 characters")
        row["text"] = normalized
        validated.append(row)
    for row in sorted(validated, key=lambda r: pd.Timestamp(r["available_at"])):
        key = (row["ticker"], row["text"].lower())
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return sorted(unique, key=lambda r: pd.Timestamp(r["available_at"]))

def run(args):
    out = Path(args.out)
    configure_logging(out)
    news = load_news(args.news)
    price_frame = prices(args.prices)
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8")) if args.labels else []
    comparison = {}
    for version in ["v1", "v2"]:
        prompt = (Path(__file__).resolve().parents[1] / "prompts" / (version+".txt")).read_text(encoding="utf-8")
        predictions, returns, errors, operations = [], [], [], []
        for item in news:
            payload = {k: item[k] for k in ["ticker", "text", "published_at"]}
            try:
                signal, meta = structured_call(Signal, prompt, payload, args.cache,
                    args.provider, args.model if args.provider == "openai" else "keyword-"+version,
                    lambda p: offline_classifier(p, version))
                if signal.evidence not in item["text"]:
                    raise ValueError("Evidence is not an exact article substring")
                record = dict(id=item["id"], ticker=item["ticker"], provider=args.provider,
                              prompt_version=version, **signal.model_dump(),
                              direction=direction(signal.sentiment), position=position(signal))
                predictions.append(record)
                operations.append(dict(id=item["id"], **meta))
                returns.extend(forward_returns(item, price_frame, position(signal), args.cost_bps))
            except Exception as exc:
                logging.error("article_failed id=%s type=%s", item["id"], type(exc).__name__)
                errors.append({"id": item["id"], "type": type(exc).__name__, "message": str(exc)[:300]})
        metrics = classification_metrics(predictions, labels)
        metrics.update(total_articles=len(news), accepted=len(predictions), errors=len(errors),
                       acceptance_rate=len(predictions)/len(news) if news else None)
        for split in ["dev", "test"]:
            metrics[split] = classification_metrics(predictions, [x for x in labels if x.get("split") == split])
        dump(out/version/"signals.json", predictions)
        dump(out/version/"classification.json", metrics)
        dump(out/version/"errors.json", errors)
        dump(out/version/"operations.json", operations)
        dump(out/version/"forward_returns.json", returns)
        dump(out/version/"event_study.json", summarize(returns))
        comparison[version] = {k: metrics[k] for k in ["accepted", "errors", "direction_accuracy", "event_accuracy", "direction_macro_f1"]}
    dump(out/"comparison.json", comparison)
    manifest = {"provider": args.provider, "model": args.model if args.provider == "openai" else "keyword baseline",
                "data_notice": "Check data provenance. Bundled samples are SYNTHETIC, not investment evidence.",
                "cost_bps_round_trip": args.cost_bps, "entry_rule": "first close strictly after available_at + 5 minutes",
                "input_sha256": {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [args.news, args.prices]},
                "prompt_sha256": {v: hashlib.sha256((Path(__file__).resolve().parents[1]/"prompts"/(v+".txt")).read_bytes()).hexdigest() for v in ["v1", "v2"]}}
    dump(out/"manifest.json", manifest)
    print(json.dumps(comparison, indent=2))
    if news and not any(x["accepted"] for x in comparison.values()):
        raise RuntimeError("All classifications failed. Inspect errors.json and credentials/model.")

def main():
    parser = argparse.ArgumentParser(description="News event study; offline baseline or real LLM")
    parser.add_argument("--news", default="data/sample/news.jsonl")
    parser.add_argument("--prices", default="data/sample/prices.csv")
    parser.add_argument("--labels", default="evaluation/labels.json")
    parser.add_argument("--provider", choices=["offline", "openai"], default="offline")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", ""))
    parser.add_argument("--cache", default=".cache")
    parser.add_argument("--out", default="runs/demo")
    parser.add_argument("--cost-bps", type=float, default=10)
    args = parser.parse_args()
    if args.cost_bps < 0 or not __import__("math").isfinite(args.cost_bps):
        parser.error("cost-bps must be finite and nonnegative")
    run(args)

if __name__ == "__main__":
    main()
