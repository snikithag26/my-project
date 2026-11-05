"""Synthetic stand-in datasets so the project runs end to end.

Real data for Module 1: download the UCI 'Autism Screening Adult' CSV (see README) and pass it
to ml/train_asd.py with --data.  The stress dataset has no public equivalent and is simulated
by design; say so in your report.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def make_asd(n=1500, seed=42):
    rng = np.random.default_rng(seed)
    y = rng.binomial(1, 0.4, n)
    p_asd, p_non = rng.uniform(0.60, 0.85, 10), rng.uniform(0.15, 0.40, 10)
    a = np.column_stack([rng.binomial(1, np.where(y == 1, p_asd[i], p_non[i])) for i in range(10)])
    df = pd.DataFrame(a, columns=[f"A{i}_Score" for i in range(1, 11)])
    df["age"] = np.clip(rng.normal(28, 12, n), 2, 70).astype(int)
    df["gender"] = np.where(rng.random(n) < np.where(y == 1, 0.62, 0.45), "m", "f")
    df["jundice"] = np.where(rng.random(n) < np.where(y == 1, 0.20, 0.10), "yes", "no")
    df["austim"] = np.where(rng.random(n) < np.where(y == 1, 0.18, 0.06), "yes", "no")
    df["Class/ASD"] = np.where(y == 1, "YES", "NO")
    return df


def make_stress(n=3000, seed=7):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"sleep": rng.uniform(3, 10, n).round(1), "noise": rng.integers(0, 11, n), "change": rng.integers(0, 11, n),
                      "crowd": rng.integers(0, 11, n), "mood": rng.integers(1, 6, n)})
    z = -4.2 + 0.45 * np.maximum(0, 7.5 - d.sleep) + 0.38 * d.noise + 0.34 * d.change + 0.22 * d.crowd + 0.5 * (5 - d.mood) + rng.normal(0, 0.8, n)
    d["overload"] = rng.binomial(1, 1 / (1 + np.exp(-z)))
    return d


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    make_asd().to_csv(DATA / "asd_screening_synthetic.csv", index=False)
    make_stress().to_csv(DATA / "stress_synthetic.csv", index=False)
    print("Wrote data/asd_screening_synthetic.csv and data/stress_synthetic.csv")
