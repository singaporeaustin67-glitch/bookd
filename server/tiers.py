"""Subscription tiers: the source of truth for plan names, prices, and hunt limits."""

from __future__ import annotations

TIERS: dict[str, dict] = {
    "free": {
        "label": "Free",
        "price_monthly": 0,
        "price_annual": None,
        "hunt_limit": 50,  # leads sourced per calendar month
    },
    "professional": {
        "label": "Professional",
        "price_monthly": 79,
        "price_annual": 59,
        "hunt_limit": 3000,
    },
    "enterprise": {
        "label": "Enterprise",
        "price_monthly": 499,
        "price_annual": None,  # scoped
        "hunt_limit": None,  # unlimited
    },
}

DEFAULT_WORKSPACE = "local"


def tier_info(name: str) -> dict:
    if name not in TIERS:
        raise ValueError(f"unknown tier: {name}")
    return {"name": name, **TIERS[name]}


def hunt_limit(name: str) -> int | None:
    return tier_info(name)["hunt_limit"]
