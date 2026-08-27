"""Bring-your-own-key (BYOK) storage: per-workspace API keys, Fernet-encrypted at rest.

Master key comes from BOOKD_SECRET_KEY; if unset, one is generated and persisted
next to the database (data/.secret_key, gitignored) so stored keys survive restarts.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet

from . import config, db
from .tiers import DEFAULT_WORKSPACE

_ENV_KEY = os.environ.get("BOOKD_SECRET_KEY", "").strip()


def _master_key() -> bytes:
    if _ENV_KEY:
        return _ENV_KEY.encode()
    key_file = Path(config.DB_PATH).parent / ".secret_key"
    if key_file.exists():
        raw = key_file.read_text().strip().encode()
        return raw
    generated = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.touch(mode=0o600)
    key_file.write_bytes(generated)
    return generated


def _fernet() -> Fernet:
    return Fernet(_master_key())


def preview(plaintext: str) -> str:
    return f"····{plaintext[-4:]}" if len(plaintext) >= 4 else "····"


def set_key(workspace: str, provider: str, plaintext: str) -> str:
    token = _fernet().encrypt(plaintext.strip().encode()).decode()
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO api_keys (workspace, provider, token_encrypted, preview, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(workspace, provider) DO UPDATE SET
                 token_encrypted=excluded.token_encrypted, preview=excluded.preview""",
            (workspace, provider, token, preview(plaintext.strip()), db._now()),
        )
        conn.commit()
    return preview(plaintext.strip())


def get_key(workspace: str, provider: str) -> str | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT token_encrypted FROM api_keys WHERE workspace=? AND provider=?",
            (workspace, provider),
        ).fetchone()
    if not row:
        return None
    return _fernet().decrypt(row["token_encrypted"].encode()).decode()


def list_keys(workspace: str) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT provider, preview FROM api_keys WHERE workspace=?",
            (workspace,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_key(workspace: str, provider: str) -> bool:
    with db.connect() as conn:
        cur = conn.execute(
            "DELETE FROM api_keys WHERE workspace=? AND provider=?",
            (workspace, provider),
        )
        conn.commit()
        return cur.rowcount > 0


def resolve(provider: str, workspace: str = DEFAULT_WORKSPACE) -> tuple[str | None, str]:
    """Which key to use: workspace BYOK first, env var second. Returns (key, source)."""
    byok = get_key(workspace, provider)
    if byok:
        return byok, "byok"
    env_key = None
    if provider == "apollo":
        env_key = config.APOLLO_API_KEY or None
    elif provider == "hunter":
        env_key = config.HUNTER_API_KEY or None
    if env_key:
        return env_key, "env"
    return None, "none"
