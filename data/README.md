# Data Directory

This folder contains the datasets used by the application at runtime, loaded via `frontend/data_loader.py`.

| File | Purpose |
|---|---|
| `career_recommendation.csv` | The core training dataset (sourced from Kaggle, see Section 6 of the project report for citation and licensing details). Contains student profile records and the target career labels used to train the XGBoost recommendation model (`notebooks/IntProjectISI.ipynb`). |
| `career_skill_gap.csv` | Maps each target career to its required skills and recommended courses. Used by `compute_skill_gap()` in `recommender.py` to generate the personalized Skill Gap Analysis shown in the app. |
| `career_learning_path.csv` | Maps each target career to a staged learning roadmap (learning stage, priority skills, learning path, resources, duration, and milestone). Used by `get_learning_path()` in `recommender.py`. |
| `career_prediction.csv` | Loaded by `data_loader.py`. Its exact role in the current application flow needs to be reconfirmed with the team before final submission, since the primary Top-3 prediction pathway uses the trained model files (`career_model.pkl`, `label_binarizer.pkl`, `input_encoders.pkl`) rather than a CSV lookup. |

## Note on "raw" vs "processed" data

This project does not maintain separate `raw/` and `processed/` copies of these files. The datasets above are the curated, ready-to-use versions the live application reads directly. The data cleaning and feature engineering work performed on the original source data is documented separately:

- The original dataset source and licensing: Section 6.1 of the project report.
- The preprocessing and feature engineering steps performed on it: Section 6.2 of the project report, and the accompanying notebook at `notebooks/Data_Preprocessing_Feature_Engineering__1_.ipynb`.
- The final model training, using the processed features: `notebooks/IntProjectISI.ipynb`.
