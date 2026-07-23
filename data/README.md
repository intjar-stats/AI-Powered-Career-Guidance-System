# Data Directory

This folder contains the datasets used by the application at runtime, loaded via `frontend/data_loader.py`.

| File | Purpose |
|---|---|
| `career_recommendation.csv` | The core training dataset (sourced from Kaggle, see Section 6 of the project report for citation and licensing details). Contains student profile records and the target career labels used to train the XGBoost recommendation model (`notebooks/IntProjectISI.ipynb`). |
| `career_skill_gap.csv` | Contains 1,000 rows, one per synthetic student profile (Student_ID, Full_Name, Target_Career, Career_Goal, Current_Skills, Required_Skills, Gap_Percentage, Recommended_Level, Estimated_Hours, Recommended_Courses). Used by `compute_skill_gap()` in `recommender.py`, which matches on `Target_Career` and computes a live user's actual gap and hours from their own profile rather than reading the pre-computed `Gap_Percentage`/`Estimated_Hours` columns directly (see DEF-07 in the Testing Plan). |
| `career_learning_path.csv` | Contains 1,000 rows, one per synthetic student profile (Student_ID, Full_Name, Target_Career, Gap_Percentage, Priority_Skills, Learning_Stage, Learning_Path, Recommended_Resources, Estimated_Duration, Milestone). Used by `get_learning_path()` in `recommender.py`, matched on `Target_Career`. |
| `career_prediction.csv` | Per a supplementary Power BI analysis, this file also contains 1,000 rows with per-student fields (Student_ID, Gender, Age, GPA, Degree_Level, Employment_Status, Target_Career); this has not yet been independently verified the way the two files above were. Its exact role in the current application flow still needs to be reconfirmed with the team before final submission, since the primary Top-3 prediction pathway uses the trained model files (`career_model.pkl`, `label_binarizer.pkl`, `input_encoders.pkl`) rather than a CSV lookup. |

## Note on "raw" vs "processed" data

This project does not maintain separate `raw/` and `processed/` copies of these files. The datasets above are the curated, ready-to-use versions the live application reads directly. The data cleaning and feature engineering work performed on the original source data is documented separately:

- The original dataset source and licensing: Section 6.1 of the project report.
- The preprocessing and feature engineering steps performed on it: Section 6.2 of the project report, and the accompanying notebook at `notebooks/Data_Preprocessing_Feature_Engineering__1_.ipynb`.
- The final model training, using the processed features: `notebooks/IntProjectISI.ipynb`.
