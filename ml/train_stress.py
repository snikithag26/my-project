"""Module 7: train the stress / sensory-overload predictor on the simulated dataset."""
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from backend.app.ml import STRESS_FEATS
from ml.generate_data import DATA, make_stress

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[1] / "models"


def main():
    f = DATA / "stress_synthetic.csv"
    df = pd.read_csv(f) if f.exists() else make_stress()
    X, y = df[STRESS_FEATS], df["overload"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=1)
    m = RandomForestClassifier(n_estimators=250, min_samples_leaf=3, random_state=0).fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    print(f"accuracy {accuracy_score(yte, p > .5):.3f}  F1 {f1_score(yte, p > .5):.3f}  ROC-AUC {roc_auc_score(yte, p):.3f}")
    OUT.mkdir(exist_ok=True)
    joblib.dump(m, OUT / "stress_model.joblib")
    print("Saved models/stress_model.joblib")


if __name__ == "__main__":
    main()
