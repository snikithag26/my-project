from fastapi.testclient import TestClient

from backend.app.main import app

ANS = [1, 0, 0, 0, 0, 0, 1, 1, 0, 1]  # every item scored -> 10/10


def client():
    return TestClient(app)


def reg(c, email, role="parent"):
    r = c.post("/api/auth/register", json={"email": email, "password": "secret1", "name": email.split("@")[0], "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_auth_and_duplicate():
    with client() as c:
        reg(c, "a@x.com")
        assert c.post("/api/auth/register", json={"email": "a@x.com", "password": "secret1", "name": "A"}).status_code == 409
        assert c.post("/api/auth/login", json={"email": "a@x.com", "password": "nope"}).status_code == 401
        assert c.post("/api/auth/login", json={"email": "a@x.com", "password": "secret1"}).status_code == 200
        assert c.get("/api/people").status_code == 401


def test_people_roles_and_report():
    with client() as c:
        parent, teacher, therapist = reg(c, "p@x.com"), reg(c, "t@x.com", "teacher"), reg(c, "th@x.com", "therapist")
        person = {"name": "Kid", "age": "8", "details": [["School", "X & Y"]], "care": [], "helps": ["Headphones"], "faces": [], "sessions": [], "mood": [{"at": "2026-01-01", "v": 4}]}
        assert c.put("/api/people/k1", json=person, headers=parent).status_code == 200
        assert len(c.get("/api/people", headers=parent).json()) == 1
        assert len(c.get("/api/people", headers=teacher).json()) == 1
        assert c.put("/api/people/k1", json={**person, "name": "Hack"}, headers=teacher).status_code == 403
        assert c.put("/api/people/k1", json={**person, "age": "9"}, headers=therapist).status_code == 200
        r = c.get("/api/people/k1/report.pdf", headers=teacher)
        assert r.status_code == 200 and r.content.startswith(b"%PDF")
        assert c.delete("/api/people/k1", headers=teacher).status_code == 403
        assert c.delete("/api/people/k1", headers=parent).status_code == 200


def test_screening_and_assessment_log():
    with client() as c:
        h = reg(c, "s@x.com")
        c.put("/api/people/s1", json={"name": "S", "faces": []}, headers=h)
        assert len(c.get("/api/screening/questions", headers=h).json()) == 10
        hi = c.post("/api/screening/predict", json={"answers": ANS, "person_id": "s1"}, headers=h).json()
        lo = c.post("/api/screening/predict", json={"answers": [1 - a for a in ANS]}, headers=h).json()
        assert hi["score"] == 10 and hi["level"] == "High" and lo["score"] == 0 and lo["level"] == "Minimal"
        assert hi["probability"] > 0.8 > 0.2 > lo["probability"]
        assert c.get("/api/people", headers=h).json()[0]["assessments"][0]["type"] == "screening"
        assert c.post("/api/screening/predict", json={"answers": [2] * 10}, headers=h).status_code == 422


def test_stress_and_nlp():
    with client() as c:
        h = reg(c, "n@x.com")
        calm = c.post("/api/stress/predict", json={"sleep": 9, "noise": 1, "change": 0, "crowd": 1, "mood": 5}, headers=h).json()
        bad = c.post("/api/stress/predict", json={"sleep": 4, "noise": 9, "change": 8, "crowd": 8, "mood": 1}, headers=h).json()
        assert calm["level"] == "Low" and bad["level"] == "High" and bad["drivers"][0]["effect"] > 0
        s = c.post("/api/nlp/simplify", json={"text": "The teacher will commence the examination shortly, and it is imperative that you remain seated."}, headers=h).json()
        assert "start" in s["simple"] and s["grade_after"] <= s["grade_before"]


def test_static_frontend_and_health():
    with client() as c:
        assert c.get("/api/health").json()["status"] == "ok"
