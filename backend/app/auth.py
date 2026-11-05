"""Password hashing (PBKDF2) and JWT bearer authentication."""
import hashlib
import hmac
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import get_conn

SECRET = os.environ.get("AUTISPHERE_SECRET", "dev-only-change-me")
TOKEN_HOURS = 12
bearer = HTTPBearer(auto_error=False)


def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def new_salt() -> str:
    return secrets.token_hex(16)


def check_pw(password, salt, expected):
    return hmac.compare_digest(hash_pw(password, salt), expected)


def make_token(user_id: int, role: str) -> str:
    return jwt.encode({"sub": str(user_id), "role": role, "exp": int(time.time()) + TOKEN_HOURS * 3600}, SECRET, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Not logged in")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please log in again")
    with get_conn() as c:
        row = c.execute("SELECT id, email, name, role FROM users WHERE id=?", (int(payload["sub"]),)).fetchone()
    if row is None:
        raise HTTPException(401, "Unknown user")
    return dict(row)
