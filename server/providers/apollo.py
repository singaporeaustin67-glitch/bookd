"""Apollo.io provider — activates when APOLLO_API_KEY is set.

Uses Apollo's people search API. Docs: https://docs.apollo.io/
"""

from __future__ import annotations

import httpx

from .. import config
from .base import normalize

SEARCH_URL = "https://api.apollo.io/v1/mixed_people/search"


class ApolloProvider:
    name = "apollo"

    def available(self) -> bool:
        return bool(config.APOLLO_API_KEY)

    def search(self, icp: dict, limit: int) -> list[dict]:
        payload: dict = {
            "page": 1,
            "per_page": min(limit, 100),
            "person_titles": icp.get("titles") or [],
        }
        if icp.get("countries"):
            payload["person_locations"] = icp["countries"]
        if icp.get("keywords"):
            payload["q_keywords"] = " ".join(icp["keywords"])
        resp = httpx.post(
            SEARCH_URL,
            json=payload,
            headers={"X-Api-Key": config.APOLLO_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        people = resp.json().get("people", [])
        leads = []
        for p in people:
            if not p.get("email"):
                continue
            org = p.get("organization") or {}
            leads.append(
                normalize(
                    {
                        "email": p["email"],
                        "first_name": p.get("first_name", ""),
                        "last_name": p.get("last_name", ""),
                        "title": p.get("title", ""),
                        "company": org.get("name", ""),
                        "domain": org.get("primary_domain", ""),
                        "country": p.get("country", ""),
                        "industry": org.get("industry", ""),
                    },
                    self.name,
                )
            )
        return leads[:limit]
