"""Stage 05a — classify inbound reply intent (keyword scoring, LLM-upgradable)."""

from __future__ import annotations

POSITIVE = [
    "sounds good", "interested", "let's talk", "lets talk", "schedule", "book",
    "send me times", "available", "calendar", "call works", "set up a call",
    "tell me more", "yes", "sure", "happy to",
]
NEGATIVE = [
    "not interested", "no thanks", "unsubscribe", "remove me", "stop emailing",
    "don't contact", "do not contact", "wrong person", "not a fit", "pass",
]
QUESTION = ["?", "how much", "pricing", "price", "cost", "details", "more info", "case stud"]


def classify(body: str) -> str:
    text = body.lower()
    score = {"positive": 0, "negative": 0, "question": 0}
    for phrase in POSITIVE:
        if phrase in text:
            score["positive"] += 1
    for phrase in NEGATIVE:
        if phrase in text:
            score["negative"] += 2  # opt-outs weigh double — never argue with them
    for phrase in QUESTION:
        if phrase in text:
            score["question"] += 1
    if score["negative"] > 0:
        return "negative"
    if score["positive"] > 0:
        return "positive"
    if score["question"] > 0:
        return "question"
    return "neutral"
