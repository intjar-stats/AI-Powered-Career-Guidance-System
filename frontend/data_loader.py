"""
data_loader.py — loads the 4 CSV datasets used for skill-gap and roadmap lookups.

Uses paths relative to THIS FILE's location (not the current working directory),
so it works correctly no matter where Streamlit Cloud actually runs the app from.

Expects this file to sit in frontend/, with a data/ folder at the repo root
(one level up from frontend/):

    repo-root/
        data/
            career_prediction.csv
            career_recommendation.csv
            career_learning_path.csv
            career_skill_gap.csv
        frontend/
            data_loader.py   <- this file
            app.py
            ...
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")


def _load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Could not find '{filename}' at expected path: {os.path.abspath(path)}. "
            f"Check that the data/ folder exists at the repo root with all 4 CSVs."
        )


career_prediction = _load_csv("career_prediction.csv")
career_recommendation = _load_csv("career_recommendation.csv")
career_learning_path = _load_csv("career_learning_path.csv")
career_skill_gap = _load_csv("career_skill_gap.csv")


def load_data():
    return (
        career_prediction,
        career_recommendation,
        career_learning_path,
        career_skill_gap,
    )
