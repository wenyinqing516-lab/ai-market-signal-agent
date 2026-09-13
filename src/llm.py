"""Small, inspectable LLM boundary: schema validation, cache, logs, bounded retries."""
import hashlib
import json
import logging
import os
import time
from pathlib import Path

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

def configure_logging(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=Path(folder) / "run.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", force=True)

def structured_call(schema, prompt, payload, cache_dir, provider, model, offline):
    # Labels and future prices must never be included in payload.
    request = {"schema": schema.model_json_schema(), "prompt": prompt,
               "payload": payload, "provider": provider, "model": model,
               "implementation_version": "1.0"}
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    path = Path(cache_dir) / (key + ".json")
    started = time.perf_counter()
    if path.exists():
        try:
            result = schema.model_validate_json(path.read_text(encoding="utf-8"))
            logging.info("cache_hit key=%s provider=%s", key[:12], provider)
            return result, {"cache_hit": True, "latency_s": time.perf_counter()-started,
                            "attempts": 0, "usage": None}
        except (ValueError, OSError):
            logging.warning("invalid_cache key=%s", key[:12])
    if provider == "offline":
        result = schema.model_validate(offline(payload))
        meta = {"cache_hit": False, "latency_s": time.perf_counter()-started,
                "attempts": 1, "usage": None}
    else:
        if not os.getenv("OPENAI_API_KEY") or not model:
            raise ValueError("Live mode requires OPENAI_API_KEY and --model. No offline fallback.")
        from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError
        client = OpenAI(timeout=40, max_retries=0)
        for attempt in range(3):
            try:
                response = client.responses.parse(
                    model=model, store=False,
                    input=[{"role": "system", "content": prompt},
                           {"role": "user", "content": json.dumps(payload)}],
                    text_format=schema)
                if response.output_parsed is None:
                    raise ValueError("Refusal or incomplete structured output")
                result = schema.model_validate(response.output_parsed)
                meta = {"cache_hit": False, "latency_s": time.perf_counter()-started,
                        "attempts": attempt+1,
                        "usage": response.usage.model_dump() if response.usage else None}
                break
            except (RateLimitError, APIConnectionError, APIStatusError) as exc:
                retryable = isinstance(exc, (RateLimitError, APIConnectionError)) or exc.status_code >= 500
                logging.warning("api_error key=%s type=%s attempt=%d", key[:12], type(exc).__name__, attempt+1)
                if not retryable or attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    dump(path, result.model_dump())
    logging.info("validated key=%s provider=%s model=%s latency_s=%.3f",
                 key[:12], provider, model, meta["latency_s"])
    return result, meta
