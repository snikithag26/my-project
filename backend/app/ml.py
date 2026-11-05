"""Model loading and prediction (ASD screening level, stress / overload risk)."""
import math
from pathlib import Path

import joblib
import pandas as pd

MODELS = Path(__file__).resolve().parents[2] / "models"

# (question, answer that scores 1 point: 1 = agree, 0 = disagree). Paraphrased AQ-10 items.
AQ = [
    ("I often notice small sounds that others do not.", 1),
    ("I usually focus on the whole picture, not small details.", 0),
    ("I find it easy to do more than one thing at once.", 0),
    ("After an interruption, I can switch back very quickly.", 0),
    ("I find it easy to read between the lines when someone talks.", 0),
    ("I can tell when someone listening to me is getting bored.", 0),
    ("When reading a story, I find it hard to work out the characters’ intentions.", 1),
    ("I like collecting information about categories of things.", 1),
    ("I can easily tell what someone feels by looking at their face.", 0),
    ("I find it hard to work out people’s intentions.", 1),
]
ASD_FEATS = [f"A{i}" for i in range(1, 11)] + ["age", "gender_m", "jaundice", "family_asd"]
STRESS_FEATS = ["sleep", "noise", "change", "crowd", "mood"]
STRESS_BASE = {"sleep": 8, "noise": 2, "change": 1, "crowd": 2, "mood": 4}
STRESS_LABEL = {"sleep": "Low sleep", "noise": "Noise", "change": "Routine change", "crowd": "Crowds", "mood": "Low mood"}

_cache = {}


def _model(name):
    if name not in _cache:
        p = MODELS / name
        _cache[name] = joblib.load(p) if p.exists() else None
    return _cache[name]


def models_loaded():
    return {"asd": _model("asd_model.joblib") is not None, "stress": _model("stress_model.joblib") is not None}


def item_scores(answers):
    return [1 if a == AQ[i][1] else 0 for i, a in enumerate(answers)]


def _asd_prob(vec):
    m = _model("asd_model.joblib")
    if m is None:  # fallback so the app still runs before training
        return 1 / (1 + math.exp(-(sum(vec[:10]) - 5.5) / 1.3))
    return float(m.predict_proba(pd.DataFrame([vec], columns=ASD_FEATS))[0, 1])


def level_for(score):
    if score <= 2:
        return "Minimal", "Few indicators. Routine monitoring is enough."
    if score <= 5:
        return "Mild / Borderline", "Some indicators. Consider a follow-up discussion."
    if score <= 7:
        return "Moderate", "Several indicators. A specialist assessment is recommended."
    return "High", "Many indicators. Please seek a professional assessment."


def screen(answers, age, gender, jaundice, family):
    scores = item_scores(answers)
    vec = [*scores, age, 1 if gender == "m" else 0, int(jaundice), int(family)]
    p = _asd_prob(vec)
    total = sum(scores)
    level, advice = level_for(total)
    expl = []
    for i in range(10):  # flip one item at a time: how much did it move the probability?
        alt = vec.copy()
        alt[i] = 1 - alt[i]
        expl.append({"item": i + 1, "text": AQ[i][0], "scored": bool(scores[i]), "effect": round(p - _asd_prob(alt), 3)})
    expl.sort(key=lambda e: -abs(e["effect"]))
    return {"score": total, "level": level, "advice": advice, "probability": round(p, 3),
            "model": "trained classifier" if _model("asd_model.joblib") else "rule-based fallback", "explanation": expl}


def _stress_prob(vals):
    m = _model("stress_model.joblib")
    if m is None:
        z = -4.2 + 0.45 * max(0, 7.5 - vals["sleep"]) + 0.38 * vals["noise"] + 0.34 * vals["change"] + 0.22 * vals["crowd"] + 0.5 * (5 - vals["mood"])
        return 1 / (1 + math.exp(-z))
    return float(m.predict_proba(pd.DataFrame([[vals[k] for k in STRESS_FEATS]], columns=STRESS_FEATS))[0, 1])


def stress(vals):
    p = _stress_prob(vals)
    drivers = []
    for k in STRESS_FEATS:  # replace one factor with a calm baseline value
        alt = {**vals, k: STRESS_BASE[k]}
        drivers.append({"factor": STRESS_LABEL[k], "effect": round(p - _stress_prob(alt), 3)})
    drivers.sort(key=lambda d: -d["effect"])
    pct = round(p * 100)
    level, advice = (("Low", "Carry on as usual."), ("Moderate", "Plan a quiet break and keep the routine steady."), ("High", "Offer a calm space, headphones and a predictable plan."))[0 if pct < 30 else 1 if pct < 60 else 2]
    return {"risk": pct, "level": level, "advice": advice, "drivers": drivers,
            "model": "trained random forest" if _model("stress_model.joblib") else "rule-based fallback"}
