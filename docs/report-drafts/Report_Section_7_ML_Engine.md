# Final Report: Draft Section 7 (ML Recommendation Engine)

> Status: Draft for review. Author: Bhupathi Likhitha (Project Lead, ML Recommendation Engine).
> This draft was assembled from the actual training script and its output, since a
> written explanation from Likhitha was still pending at the time of drafting. It
> should be reviewed and confirmed by Likhitha before finalizing.

---

## 7. Machine Learning Recommendation Engine

### 7.1 Overview

The core of the system is a multi-label classification model that predicts a student's top three suitable careers from their profile. Since a student can reasonably be suited to more than one career, this was treated as a multi-label problem rather than a single-label one: each training record has three recommended jobs, and the model learns to predict a set of likely careers rather than a single class.

### 7.2 Dataset and Feature Set

After cleaning (removing duplicate records and filling missing values), the dataset used for training contained 2,000 records across 25 columns. The final feature set used for training consists of 22 input features:

- Six profile fields: age, gender, degree level, field of study, GPA, and years of experience.
- Eleven technical skill ratings: Python, Java, C/C++, SQL, Machine Learning, Data Analysis, Cloud Computing, Cybersecurity, Web Development, DevOps, and Networking.
- Five soft skill ratings: Communication, Leadership, Problem Solving, Teamwork, and Adaptability.

Three categorical fields (gender, degree level, and field of study) were label-encoded, each with its own separate encoder, fitted directly on the original text values. The trained categories were:

- Gender: Female, Male
- Degree level: Bachelor, Master, PhD
- Field of study: AI, Computer Science, Cybersecurity, Data Science, Software Engineering

This matches what was independently found by testing the deployed application directly (Section 10.3 and the Testing Plan's findings on the Gender and Field of Study fields), confirming that the model in production was trained on exactly this feature set.

The target is a set of thirteen possible career labels: AI Researcher, Backend Developer, Business Intelligence Analyst, Cloud Engineer, Cybersecurity Analyst, Data Analyst, Data Scientist, DevOps Engineer, Frontend Developer, Full Stack Developer, Machine Learning Engineer, Security Engineer, and Software Engineer. These were encoded using a multi-label binarizer, since each record has three associated careers rather than one.

### 7.3 Model Comparison

Four classification algorithms were trained and compared on an 80/20 train-test split (1,600 training records, 400 test records; a fixed random seed of 42 was used throughout for reproducibility), each wrapped in a one-vs-rest strategy to handle the multi-label output. Model quality was compared using micro-averaged F1 score, which aggregates precision and recall across all classes and all three predicted career slots.

| Model | Micro F1 Score |
|---|---|
| K-Nearest Neighbors (KNN) | 0.4887 |
| Decision Tree | 0.9164 |
| Random Forest | 0.9039 |
| **XGBoost** | **0.9645** |

XGBoost gave the strongest result by a clear margin and was selected as the final model. KNN performed noticeably worse than the other three, likely because distance-based methods are less effective on this kind of mixed numerical and categorical feature set without additional feature scaling or weighting. Interestingly, the single Decision Tree slightly outperformed the Random Forest ensemble on this dataset; this can happen when the dataset's decision boundaries are relatively clean and an ensemble's averaging effect gives back some sharpness that a single well-tuned tree retains. XGBoost's gradient-boosted approach, which corrects errors iteratively rather than averaging independent trees, achieved the best balance of precision and recall across nearly all thirteen career classes.

### 7.4 Model Evaluation in Detail

Looking beyond the overall F1 score, performance varied noticeably across the thirteen career classes, and this variation follows a consistent pattern across all four models: classes with more training examples were predicted more reliably, and classes with very few examples were predicted poorly regardless of which algorithm was used.

The clearest example is "Full Stack Developer," which had only 7 examples in the test set (out of 400 test profiles, each contributing up to three career labels). Every model struggled with this class specifically: XGBoost, the best-performing model overall, still only achieved a recall of 0.14 and an F1 score of 0.25 for this one class, far below its otherwise strong performance elsewhere (most other classes scored above 0.90). "Data Analyst" (10 test examples) and "Security Engineer" (21 test examples) showed a similar, if less severe, pattern.

This points to a class imbalance in the underlying dataset: some career labels are simply rarer than others in the source data, giving the model fewer examples to learn from. It does not affect the majority of predictions (most career classes had over 100 test examples and were predicted reliably), but it is a real limitation worth stating plainly rather than hiding behind the strong overall F1 score. This is separate from, but related to, an observation raised during application testing that some contrasting student profiles received identical top-3 predictions (Testing Plan, Section 3.5); both point toward the same underlying area for improvement: the training data's balance and diversity across career labels.

### 7.5 Final Model Artifacts

Training produces three files that the application loads at runtime: the trained classifier (`career_model.pkl`), the multi-label binarizer that maps the model's numeric output back to career names (`label_binarizer.pkl`), and the three input encoders bundled together (`input_encoders.pkl`). These three files are loaded once when the application starts (Section 11) and used for every prediction served by the deployed app.

The training script and its output are available in the repository at `notebooks/IntProjectISI.ipynb`. The script itself was written by Likhitha; it was executed in Google Colab by Md Intjar (since direct access to Likhitha's own notebook was not available at the time) to regenerate the three model artifacts and confirm the results shown in Section 7.3.

---

> **Editorial note for report assembly:** This draft resolves the open question noted in Section 6.2 about a mismatch between the preprocessing stage's feature set and the final model's feature set. The training script confirms the final model uses exactly the 22 features and 3 categorical encoders described here, matching `predictor.py` exactly. The broader feature set explored during initial preprocessing (Section 6.2) was evidently narrowed down during model development; Section 6.2's note can be updated to reflect this as confirmed rather than pending. This section should still be reviewed by Likhitha for accuracy and to add any additional context on the model development process that isn't visible from the code and output alone.
