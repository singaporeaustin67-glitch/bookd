"""Local provider: searches leads the user imported into the BOOKD database.

This is the always-available source — your own list, trade-show scans, inbound
signups, anything you legitimately hold. Imported via POST /api/leads/import.
"""

from __future__ import annotations

from .. import db
from .base import normalize


class LocalProvider:
    name = "local_db"

    def available(self) -> bool:
        return True

    def search(self, icp: dict, limit: int) -> list[dict]:
        clauses, params = [], []
        if icp.get("countries"):
            placeholders = ",".join("?" for _ in icp["countries"])
            clauses.append(f"LOWER(country) IN ({placeholders})")
            params += [c.lower() for c in icp["countries"]]
        if icp.get("industries"):
            like = " OR ".join("LOWER(industry) LIKE ?" for _ in icp["industries"])
            clauses.append(f"({like})")
            params += [f"%{i.lower()}%" for i in icp["industries"]]
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with db.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM leads {where} ORDER BY id LIMIT ?", (*params, limit)
            ).fetchall()
        return [normalize(dict(r), self.name) for r in rows]
