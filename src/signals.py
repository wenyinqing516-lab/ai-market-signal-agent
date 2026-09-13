from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentiment: float = Field(ge=-1, le=1, allow_inf_nan=False)
    event: Literal["Earnings", "Guidance", "Regulation", "Product", "Macro", "Other"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    expected_horizon: Literal["1d", "5d", "20d"]
    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)

def direction(sentiment):
    return "bullish" if sentiment > 0.2 else "bearish" if sentiment < -0.2 else "neutral"

def position(signal):
    if signal.confidence < 0.6:
        return 0
    return {"bullish": 1, "bearish": -1, "neutral": 0}[direction(signal.sentiment)]

def offline_classifier(payload, version="v1"):
    """Transparent keyword baseline. This is NOT an LLM or a simulated API response."""
    text = payload["text"].lower()
    groups = [("Earnings", ["earnings", "revenue", "profit"]),
              ("Guidance", ["guidance", "outlook"]),
              ("Regulation", ["regulator", "antitrust", "fine"]),
              ("Product", ["launch", "product"]), ("Macro", ["rates", "inflation"])]
    if version == "v2":
        groups[0], groups[1] = groups[1], groups[0]
    event = next((event for event, words in groups if any(w in text for w in words)), "Other")
    positive = any(w in text for w in ["beat", "raised", "approval", "strong", "cut rates"])
    negative = any(w in text for w in ["miss", "lowered", "fine", "delay", "weak", "raise rates"])
    score = 0.7 if positive else -0.7 if negative else 0.0
    confidence = 0.75
    if version == "v2" and ("rumor" in text or "unconfirmed" in text or "no evidence" in text or (positive and negative)):
        score, confidence = 0.0, 0.4
    return dict(sentiment=score, event=event, confidence=confidence, expected_horizon="5d",
                evidence=payload["text"], reason="Offline keyword rule; not LLM reasoning.")
