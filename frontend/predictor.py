"""
predictor.py — Career prediction using Likhitha's trained XGBoost model.

Expects three artifacts in the app root (Task 7 deliverables from Likhitha):
    - career_model.pkl      : trained OneVsRestClassifier(XGBClassifier)
    - label_binarizer.pkl   : fitted MultiLabelBinarizer (career label order)
    - input_encoders.pkl    : dict of {"gender": LabelEncoder, "degree_level": LabelEncoder,
                                        "field_of_study": LabelEncoder}

If these files are missing, the app should show a clear error instead of
crashing — see ModelNotLoadedError / is_ready below.
"""

import os
import joblib
import numpy as np
import pandas as pd

# Paths relative to THIS FILE's location (not the working directory) — these
# three .pkl files should sit alongside app.py in the frontend/ folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "career_model.pkl")
BINARIZER_PATH = os.path.join(BASE_DIR, "label_binarizer.pkl")
ENCODERS_PATH = os.path.join(BASE_DIR, "input_encoders.pkl")

# Must exactly match the column order used in Likhitha's Step 5 (Feature Matrix)
FEATURE_ORDER = [
    "age", "gender", "degree_level", "field_of_study", "gpa", "years_experience",
    "python", "java", "c_cpp", "sql", "machine_learning", "data_analysis",
    "cloud_computing", "cybersecurity", "web_development", "devops", "networking",
    "communication", "leadership", "problem_solving", "teamwork", "adaptability",
]

CATEGORICAL_FIELDS = ["gender", "degree_level", "field_of_study"]

# Values the model was actually trained on — verify against Likhitha's
# `career['degree_level'].unique()` before final freeze
KNOWN_DEGREE_LEVELS = ["Bachelor", "Master", "PhD"]


class ModelNotLoadedError(RuntimeError):
    """Raised when a prediction is attempted before model artifacts are available."""
    pass


class CareerPredictor:
    """Loads model artifacts once and serves Top-3 career predictions."""

    def __init__(self):
        self.model = None
        self.mlb = None
        self.encoders = None
        self.load_error = None
        self._load()

    def _load(self):
        try:
            self.model = joblib.load(MODEL_PATH)
            self.mlb = joblib.load(BINARIZER_PATH)
            self.encoders = joblib.load(ENCODERS_PATH)
        except FileNotFoundError:
            self.load_error = (
                "Model artifacts not found (career_model.pkl / label_binarizer.pkl / "
                "input_encoders.pkl). This is a pending integration dependency — "
                "see Task 7. Place these three files in the app root directory."
            )
        except Exception as e:  # noqa: BLE001 — deliberately broad: any load failure
            self.load_error = f"Failed to load model artifacts: {e}"

    @property
    def is_ready(self) -> bool:
        return self.load_error is None

    def _encode_profile(self, profile: dict) -> pd.DataFrame:
        missing = [c for c in FEATURE_ORDER if c not in profile]
        if missing:
            raise ValueError(f"Missing required profile fields: {missing}")

        row = {col: profile[col] for col in FEATURE_ORDER}
        df = pd.DataFrame([row], columns=FEATURE_ORDER)

        for col in CATEGORICAL_FIELDS:
            encoder = self.encoders.get(col)
            if encoder is None:
                raise ValueError(
                    f"No encoder found for '{col}' in input_encoders.pkl — "
                    f"check Likhitha's export includes all three separate encoders."
                )
            value = str(df.loc[0, col])
            if value not in encoder.classes_:
                raise ValueError(
                    f"'{value}' is not a value the model was trained on for '{col}'. "
                    f"Supported values: {list(encoder.classes_)}"
                )
            df[col] = encoder.transform([value])

        return df

    def predict_top3(self, profile: dict) -> list[dict]:
        """
        Returns a list of exactly 3 dicts: [{"career": str, "confidence": float}, ...]
        ordered by descending confidence.

        NOTE: This replaces Likhitha's original `recommend_with_scores()` from the
        notebook, which had an indexing bug (`p[0][1]` after `enumerate(probabilities)`)
        that does not match sklearn's actual OneVsRestClassifier.predict_proba() output
        shape. This version uses np.argsort against the standard (n_samples, n_classes)
        probability array, which is robust regardless of sklearn version quirks.
        """
        if not self.is_ready:
            raise ModelNotLoadedError(self.load_error)

        X = self._encode_profile(profile)
        proba = np.asarray(self.model.predict_proba(X))  # shape (1, n_classes)
        row_proba = proba[0]

        top3_idx = np.argsort(row_proba)[::-1][:3]
        return [
            {"career": str(self.mlb.classes_[i]), "confidence": round(float(row_proba[i]), 4)}
            for i in top3_idx
        ]


# Module-level singleton — Streamlit's st.cache_resource in app.py ensures
# this __init__ (and the joblib.load calls) only runs once per session, not
# on every rerun/button click.
def get_predictor() -> CareerPredictor:
    return CareerPredictor()
