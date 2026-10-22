"""Single-admin authentication with signed session cookies (stdlib only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from . import config, db

_ITER = 200_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def has_user() -> bool:
    with db.connect() as conn:
        return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


def create_user(username: str, password: str) -> None:
    with db.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO users (username,pwhash,created) VALUES (?,?,?)",
                     (username, hash_password(password), int(time.time())))


def check_login(username: str, password: str) -> bool:
    with db.connect() as conn:
        row = conn.execute("SELECT pwhash FROM users WHERE username=?", (username,)).fetchone()
    return bool(row) and verify_password(password, row["pwhash"])


def change_password(username: str, old: str, new: str) -> bool:
    if not check_login(username, old):
        return False
    create_user(username, new)
    return True


# --- session tokens ------------------------------------------------------------

def make_token(username: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"u": username, "exp": int(time.time()) + config.SESSION_MAX_AGE}).encode()
    ).rstrip(b"=")
    sig = hmac.new(config.secret_key(), payload, hashlib.sha256).hexdigest()[:32]
    return f"{payload.decode()}.{sig}"


def read_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    expect = hmac.new(config.secret_key(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        pad = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + pad))
    except Exception:
        return None
    if data.get("exp", 0) < time.time():
        return None
    return data.get("u")


# --- API token (gépi hozzáférés, pl. az MCP szerver számára) -------------------
TOKEN_PREFIX = "codp_"
_TOKEN_HASH = "api_token_hash"
_TOKEN_HINT = "api_token_hint"
_TOKEN_CREATED = "api_token_created"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_api_token() -> str:
    """Új tokent készít (a régi azonnal érvénytelen). Csak most látható egyszer."""
    token = TOKEN_PREFIX + secrets.token_hex(24)
    db.set_setting(_TOKEN_HASH, _token_hash(token))
    db.set_setting(_TOKEN_HINT, token[-6:])
    db.set_setting(_TOKEN_CREATED, str(int(time.time())))
    return token


def check_api_token(token: str | None) -> bool:
    stored = db.get_setting(_TOKEN_HASH)
    if not token or not stored:
        return False
    return hmac.compare_digest(_token_hash(token), stored)


def revoke_api_token() -> None:
    for key in (_TOKEN_HASH, _TOKEN_HINT, _TOKEN_CREATED):
        db.set_setting(key, "")


def api_token_info() -> dict[str, object]:
    created = db.get_setting(_TOKEN_CREATED) or ""
    return {
        "exists": bool(db.get_setting(_TOKEN_HASH)),
        "hint": db.get_setting(_TOKEN_HINT) or "",
        "created": int(created) if created.isdigit() else None,
    }
