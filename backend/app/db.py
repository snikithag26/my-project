"""SQLite storage: users and people (one JSON document per person)."""
import json
import os
import sqlite3
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("AUTISPHERE_DB", ROOT / "data" / "autisphere.db"))
VIEW_ALL = ("teacher", "therapist")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL,
                salt TEXT NOT NULL, pw_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS people(
                id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, data TEXT NOT NULL,
                updated TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL,
                at TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(person_id, at));
            """
        )


def _can_view(user, owner_id):
    return owner_id == user["id"] or user["role"] in VIEW_ALL


def _can_edit(user, owner_id):
    return owner_id == user["id"] or user["role"] == "therapist"


def _sessions(c, pid, legacy=()):
    """Saved live sessions (newest first). `legacy` = sessions that older versions kept inside the person JSON."""
    rows = c.execute("SELECT data FROM sessions WHERE person_id=? ORDER BY at DESC", (pid,)).fetchall()
    out = [json.loads(r["data"]) for r in rows]
    seen = {s.get("at") for s in out}
    out += [s for s in legacy if isinstance(s, dict) and s.get("at") not in seen]
    out.sort(key=lambda s: s.get("at", ""), reverse=True)
    return out


def _person(c, pid, raw):
    d = json.loads(raw)
    d["sessions"] = _sessions(c, pid, d.get("sessions", []))
    d["id"] = pid
    return d


def _store_session(c, pid, s):
    c.execute("INSERT OR IGNORE INTO sessions(person_id, at, data) VALUES(?,?,?)", (pid, s["at"], json.dumps(s)))


def list_people(user):
    with get_conn() as c:
        if user["role"] in VIEW_ALL:
            rows = c.execute("SELECT id, data FROM people ORDER BY updated").fetchall()
        else:
            rows = c.execute("SELECT id, data FROM people WHERE owner_id=? ORDER BY updated", (user["id"],)).fetchall()
        return [_person(c, r["id"], r["data"]) for r in rows]


def get_person(pid, user):
    """Return the person dict, None if missing, or raise PermissionError."""
    with get_conn() as c:
        r = c.execute("SELECT owner_id, data FROM people WHERE id=?", (pid,)).fetchone()
        if r is None:
            return None
        if not _can_view(user, r["owner_id"]):
            raise PermissionError
        return _person(c, pid, r["data"])


def upsert_person(pid, user, data):
    data = {**data, "id": pid}
    sessions = data.pop("sessions", None) or []  # sessions live in their own table
    with get_conn() as c:
        r = c.execute("SELECT owner_id FROM people WHERE id=?", (pid,)).fetchone()
        if r is None:
            c.execute("INSERT INTO people(id, owner_id, data) VALUES(?,?,?)", (pid, user["id"], json.dumps(data)))
        elif _can_edit(user, r["owner_id"]):
            c.execute("UPDATE people SET data=?, updated=CURRENT_TIMESTAMP WHERE id=?", (json.dumps(data), pid))
        else:
            raise PermissionError
        for s in sessions:  # also migrates sessions from older versions; never deletes any
            if isinstance(s, dict) and isinstance(s.get("at"), str):
                _store_session(c, pid, s)
    return data


def add_session(pid, user, session):
    """Store one finished live session. Returns None if the person does not exist."""
    with get_conn() as c:
        r = c.execute("SELECT owner_id FROM people WHERE id=?", (pid,)).fetchone()
        if r is None:
            return None
        if not _can_view(user, r["owner_id"]):
            raise PermissionError
        _store_session(c, pid, session)
    return session


def delete_person(pid, user):
    with get_conn() as c:
        r = c.execute("SELECT owner_id FROM people WHERE id=?", (pid,)).fetchone()
        if r is None:
            return False
        if r["owner_id"] != user["id"]:
            raise PermissionError
        c.execute("DELETE FROM sessions WHERE person_id=?", (pid,))
        c.execute("DELETE FROM people WHERE id=?", (pid,))
    return True

# ---- One person per account ----------------------------------------------
# Fields that must be filled before the app unlocks. Rename to match your form.
REQUIRED_FIELDS = ("name", "age", "photo")


def get_my_profile(user):
    """The single person owned by this account (the oldest one, if legacy data has several)."""
    with get_conn() as c:
        r = c.execute(
            "SELECT id, data FROM people WHERE owner_id=? ORDER BY rowid LIMIT 1",
            (user["id"],),
        ).fetchone()
        return _person(c, r["id"], r["data"]) if r else None


def profile_is_complete(user):
    p = get_my_profile(user)
    return bool(p) and all(p.get(f) not in (None, "", []) for f in REQUIRED_FIELDS)


def save_my_profile(user, data):
    """Create or update the account's only person. Raises ValueError if required fields are missing."""
    missing = [f for f in REQUIRED_FIELDS if data.get(f) in (None, "", [])]
    if missing:
        raise ValueError("Missing: " + ", ".join(missing))
    existing = get_my_profile(user)
    pid = existing["id"] if existing else "p" + uuid.uuid4().hex[:12]
    data = {k: v for k, v in data.items() if k not in ("id", "sessions")}
    return upsert_person(pid, user, data)