from .signals import direction

def classification_metrics(predictions, labels):
    gold = {r["id"]: r for r in labels}
    paired = [(p, gold[p["id"]]) for p in predictions if p["id"] in gold]
    def accuracy(key, expected):
        return sum(p[key] == g[expected] for p, g in paired) / len(paired) if paired else None
    f1s = []
    for label in ["bullish", "bearish", "neutral"]:
        tp = sum(p["direction"] == label and g["direction"] == label for p, g in paired)
        fp = sum(p["direction"] == label and g["direction"] != label for p, g in paired)
        fn = sum(p["direction"] != label and g["direction"] == label for p, g in paired)
        f1s.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0)
    confusion = {g: {p: 0 for p in ["bullish", "bearish", "neutral"]} for g in ["bullish", "bearish", "neutral"]}
    failures = []
    for p, g in paired:
        confusion[g["direction"]][p["direction"]] += 1
        if p["direction"] != g["direction"] or p["event"] != g["event"]:
            failures.append({"id": p["id"], "predicted": [p["direction"], p["event"]],
                             "expected": [g["direction"], g["event"]]})
    return {"labeled_successes": len(paired), "direction_accuracy": accuracy("direction", "direction"),
            "event_accuracy": accuracy("event", "event"), "direction_macro_f1": sum(f1s)/3 if paired else None,
            "confusion_gold_rows": confusion, "failures": failures}
