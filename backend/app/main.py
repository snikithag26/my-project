"""AutiSphere API. Run: uvicorn backend.app.main:app --reload"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, db, ml, nlp, reports

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield


app = FastAPI(title="AutiSphere API", version="1.0", lifespan=lifespan)


# ---------- schemas ----------
class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=100)
    name: str = Field(min_length=1, max_length=80)
    role: Literal["parent", "teacher", "therapist"] = "parent"


class LoginIn(BaseModel):
    email: str
    password: str


class ScreenIn(BaseModel):
    answers: list[int] = Field(min_length=10, max_length=10)
    age: int = Field(default=18, ge=1, le=100)
    gender: Literal["m", "f"] = "m"
    jaundice: bool = False
    family_asd: bool = False
    person_id: Optional[str] = None


class StressIn(BaseModel):
    sleep: float = Field(ge=0, le=14)
    noise: float = Field(ge=0, le=10)
    change: float = Field(ge=0, le=10)
    crowd: float = Field(ge=0, le=10)
    mood: float = Field(ge=1, le=5)
    person_id: Optional[str] = None


class SessionIn(BaseModel):
    at: str = Field(min_length=10, max_length=40)
    secs: int = Field(ge=0, le=86400)
    parts: str = Field(max_length=400)
    dist: dict[str, float] = {}
    timeline: list[str] = Field(default=[], max_length=300)


class SimplifyIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log_assessment(pid, user, entry):
    """Attach a result to the person's record when the caller may edit it."""
    if not pid:
        return
    try:
        p = db.get_person(pid, user)
        if p is not None:
            p.setdefault("assessments", []).append(entry)
            p["assessments"] = p["assessments"][-30:]
            db.upsert_person(pid, user, p)
    except PermissionError:
        pass


# ---------- auth ----------
@app.post("/api/auth/register")
def register(body: RegisterIn):
    salt = auth.new_salt()
    try:
        with db.get_conn() as c:
            cur = c.execute("INSERT INTO users(email,name,role,salt,pw_hash) VALUES(?,?,?,?,?)",
                            (body.email.lower(), body.name, body.role, salt, auth.hash_pw(body.password, salt)))
            uid = cur.lastrowid
    except Exception:
        raise HTTPException(409, "That email is already registered")
    return {"token": auth.make_token(uid, body.role), "user": {"id": uid, "name": body.name, "role": body.role, "email": body.email.lower()}}


@app.post("/api/auth/login")
def login(body: LoginIn):
    with db.get_conn() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)).fetchone()
    if u is None or not auth.check_pw(body.password, u["salt"], u["pw_hash"]):
        raise HTTPException(401, "Wrong email or password")
    return {"token": auth.make_token(u["id"], u["role"]), "user": {"id": u["id"], "name": u["name"], "role": u["role"], "email": u["email"]}}


@app.get("/api/me")
def me(user=Depends(auth.current_user)):
    return user


# ---------- people ----------
@app.get("/api/people")
def people(user=Depends(auth.current_user)):
    return db.list_people(user)


@app.put("/api/people/{pid}")
def put_person(pid: str, body: dict, user=Depends(auth.current_user)):
    if not pid or len(pid) > 64 or not isinstance(body.get("name", ""), str):
        raise HTTPException(422, "Invalid person")
    try:
        existing = db.get_person(pid, user)
        if existing:  # keep server-side assessments that the browser may not have yet
            server = {a["at"]: a for a in existing.get("assessments", [])}
            server.update({a["at"]: a for a in body.get("assessments", [])})
            body["assessments"] = sorted(server.values(), key=lambda a: a["at"])[-30:]
        return db.upsert_person(pid, user, body)
    except PermissionError:
        raise HTTPException(403, "You can view this person but not edit them")


@app.delete("/api/people/{pid}")
def del_person(pid: str, user=Depends(auth.current_user)):
    try:
        if not db.delete_person(pid, user):
            raise HTTPException(404, "Not found")
    except PermissionError:
        raise HTTPException(403, "Only the owner can delete a person")
    return {"deleted": pid}


@app.post("/api/people/{pid}/sessions")
def add_session(pid: str, body: SessionIn, user=Depends(auth.current_user)):
    try:
        saved = db.add_session(pid, user, body.model_dump())
    except PermissionError:
        raise HTTPException(403, "No access")
    if saved is None:
        raise HTTPException(404, "Not found")
    return saved


@app.get("/api/people/{pid}/report.pdf")
def report(pid: str, user=Depends(auth.current_user)):
    try:
        p = db.get_person(pid, user)
    except PermissionError:
        raise HTTPException(403, "No access")
    if p is None:
        raise HTTPException(404, "Not found")
    return Response(reports.build_report(p, user), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="autisphere-{pid}.pdf"'})


# ---------- ML / NLP ----------
@app.get("/api/screening/questions")
def questions(user=Depends(auth.current_user)):
    return [q for q, _ in ml.AQ]


@app.post("/api/screening/predict")
def screening(body: ScreenIn, user=Depends(auth.current_user)):
    if any(a not in (0, 1) for a in body.answers):
        raise HTTPException(422, "Answers must be 1 (agree) or 0 (disagree)")
    r = ml.screen(body.answers, body.age, body.gender, body.jaundice, body.family_asd)
    _log_assessment(body.person_id, user, {"type": "screening", "at": _now(), "score": r["score"], "level": r["level"], "probability": r["probability"]})
    return r


@app.post("/api/stress/predict")
def stress(body: StressIn, user=Depends(auth.current_user)):
    r = ml.stress(body.model_dump(exclude={"person_id"}))
    if body.person_id and r["risk"] >= 60:  # only log notable forecasts
        _log_assessment(body.person_id, user, {"type": "stress", "at": _now(), "risk": r["risk"], "level": r["level"]})
    return r


@app.post("/api/nlp/simplify")
def simplify(body: SimplifyIn, user=Depends(auth.current_user)):
    return nlp.simplify(body.text)


@app.get("/api/health")
def health():
    return {"status": "ok", "models": ml.models_loaded()}


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="web")