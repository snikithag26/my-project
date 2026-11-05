"""Module 1: compare 7 classifiers (+ tuned Random Forest), save the best.

python -m ml.train_asd                        # synthetic data
python -m ml.train_asd --data data/Autism-Adult-Data.csv   # real UCI CSV
"""
import argparse
import warnings
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from backend.app.ml import ASD_FEATS
from ml.generate_data import DATA, make_asd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[1] / "models"
YES = {"yes", "y", "1", "true", "m"}


def load(path):
    df = pd.read_csv(path) if path else make_asd()
    df.columns = [c.strip() for c in df.columns]
    pick = lambda *names: next(c for c in df.columns if c.lower() in names)
    X = pd.DataFrame({f"A{i}": pd.to_numeric(df[pick(f"a{i}_score")], errors="coerce") for i in range(1, 11)})
    X["age"] = pd.to_numeric(df[pick("age")], errors="coerce")
    X["gender_m"] = df[pick("gender")].astype(str).str.lower().str.strip().isin(YES).astype(int)
    X["jaundice"] = df[pick("jundice", "jaundice")].astype(str).str.lower().str.strip().isin(YES).astype(int)
    X["family_asd"] = df[pick("austim", "autism", "family_asd")].astype(str).str.lower().str.strip().isin(YES).astype(int)
    y = df[df.columns[-1]].astype(str).str.lower().str.strip().isin(YES | {"yes"}).astype(int)
    X["age"] = X["age"].fillna(X["age"].median())
    ok = X.notna().all(axis=1)
    return X[ok][ASD_FEATS], y[ok]


def candidates():
    scaled = lambda m: make_pipeline(StandardScaler(), m)
    try:
        from xgboost import XGBClassifier
        boost = ("XGBoost", XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1, eval_metric="logloss", verbosity=0))
    except Exception:
        boost = ("HistGradientBoosting", HistGradientBoostingClassifier(random_state=0))
    return [("Logistic Regression", scaled(LogisticRegression(max_iter=1000))), ("SVM (RBF)", scaled(SVC(probability=True, random_state=0))),
            ("KNN", scaled(KNeighborsClassifier(n_neighbors=7))), ("Decision Tree", DecisionTreeClassifier(max_depth=5, random_state=0)),
            ("Random Forest", RandomForestClassifier(n_estimators=200, random_state=0)), boost,
            ("ANN (MLP)", scaled(MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=800, random_state=0)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    args = ap.parse_args()
    X, y = load(args.data)
    print(f"{len(X)} rows, {y.mean():.0%} positive")
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    models = candidates()
    gs = GridSearchCV(RandomForestClassifier(random_state=0), {"n_estimators": [100, 300], "max_depth": [4, 8, None], "min_samples_leaf": [1, 3]}, cv=cv, scoring="f1", n_jobs=-1).fit(Xtr, ytr)
    models.append(("Random Forest (tuned)", gs.best_estimator_))
    rows, fitted = [], {}
    for name, m in models:
        cvf1 = cross_val_score(m, Xtr, ytr, cv=cv, scoring="f1").mean()
        m.fit(Xtr, ytr)
        pr, pp = m.predict(Xte), m.predict_proba(Xte)[:, 1]
        rows.append({"Model": name, "CV F1": cvf1, "Accuracy": accuracy_score(yte, pr), "Precision": precision_score(yte, pr), "Recall": recall_score(yte, pr), "F1": f1_score(yte, pr), "ROC-AUC": roc_auc_score(yte, pp)})
        fitted[name] = m
    res = pd.DataFrame(rows).sort_values(["F1", "ROC-AUC"], ascending=False).round(4)
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "asd_comparison.csv", index=False)
    print(res.to_string(index=False))
    best = res.iloc[0]["Model"]
    joblib.dump(fitted[best], OUT / "asd_model.joblib")
    print(f"\nSaved best model: {best}")

    ax = res.set_index("Model")[["Accuracy", "F1", "ROC-AUC"]].plot.barh(figsize=(8, 5), ylim=(0, 1))
    ax.set_xlim(0.5, 1); plt.title("Model comparison (test set)"); plt.tight_layout(); plt.savefig(OUT / "asd_comparison.png", dpi=130); plt.close()
    ConfusionMatrixDisplay.from_estimator(fitted[best], Xte, yte, cmap="Blues"); plt.title(f"Confusion matrix: {best}"); plt.tight_layout(); plt.savefig(OUT / "asd_confusion.png", dpi=130); plt.close()
    pi = permutation_importance(fitted[best], Xte, yte, n_repeats=10, random_state=0, scoring="f1")
    pd.Series(pi.importances_mean, index=X.columns).sort_values().plot.barh(figsize=(7, 5)); plt.title("Permutation importance"); plt.tight_layout(); plt.savefig(OUT / "asd_importance.png", dpi=130); plt.close()
    try:  # optional SHAP
        import shap
        ex = shap.Explainer(fitted[best].predict_proba, Xtr.sample(100, random_state=0))
        sv = ex(Xte.sample(100, random_state=0))
        shap.plots.beeswarm(sv[..., 1], show=False); plt.tight_layout(); plt.savefig(OUT / "asd_shap.png", dpi=130); plt.close()
    except Exception as e:
        print("SHAP plot skipped:", type(e).__name__)


if __name__ == "__main__":
    main()
