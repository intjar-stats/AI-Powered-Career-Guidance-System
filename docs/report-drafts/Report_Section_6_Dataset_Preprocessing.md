# Final Report: Draft Section 6 (Dataset & Preprocessing)

> **Status:** Draft for review. Combines Aman Sawan's (Dataset & Career Mapping)
> and Uppala Lahari's (Data Preprocessing & Features) work. One item needs
> confirmation from Likhitha before this is finalized (see the note at the
> end of 6.2.

---

## 6. Dataset and Preprocessing

### 6.1 Dataset Source

The training dataset was sourced from Kaggle: *Career Path Recommendation*, published by user hafsaatm, available at
https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation. The dataset's license is not specified by the uploader; it was used here for academic and internship purposes with full attribution.

The dataset contains student profile records, including demographic details, academic performance, work experience, and self-rated technical and soft skills, along with a target career label. Before use, the CGPA field (originally on a 4-point scale) was converted to a 10-point scale, matching Indian academic convention, using linear scaling (multiplied by 2.5).

Three supporting datasets used by the application (career-to-skill-gap mapping, learning paths, and recommended courses) were prepared by the team rather than sourced externally, since no public dataset covers this mapping in the form the application needed. Their content was generated using Claude (Anthropic) against a defined set of criteria for each career, and independently cross-checked using ChatGPT (OpenAI) before the team reviewed them for relevance to the career labels produced by the ML model.

### 6.2 Data Preprocessing and Feature Engineering

The dataset was checked for quality before use: loading it with Pandas and inspecting it with `head()`, `info()`, and `describe()` showed no missing values and no duplicate records, so no cleaning beyond this verification was required.

**Feature engineering.** Five new features were derived from the raw columns to give the model more structured signals to learn from:

| Engineered Feature | Source Column(s) | Description |
|---|---|---|
| Skill_Score | Python, SQL, Machine Learning, TensorFlow, DSA, Statistics | Total technical skill score, summed from individual skill ratings |
| Experience_Level | Years of Experience | Categorized into Beginner, Intermediate, Advanced |
| GPA_Category | GPA | Categorized into Low, Average, Good, Excellent |
| Project_Level | Project Count | Categorized into Beginner, Intermediate, Advanced |
| Certification_Level | Certification Count | Categorized into None, Basic, Advanced |

**Feature encoding.** Since machine learning models need numerical input, categorical columns were converted using Label Encoding (Scikit-Learn). A separate `LabelEncoder` was fitted per categorical column, and all fitted encoders were saved together as `input_encoders.pkl`, so that new user inputs at prediction time are transformed the same way they were during training.

**Train-test split.** The dataset was split 80/20 into training and testing sets using Scikit-Learn's `train_test_split()` (random state 42), giving 800 training records and 200 testing records.

**Deliverables from this stage:** a Jupyter notebook documenting the full preprocessing workflow (linked in the repository), the processed training and testing datasets, and `input_encoders.pkl`.

> **Note for final review:** This preprocessing stage encoded a broader set of categorical fields (including status, industry, and goal-related columns) than the three fields (`gender`, `degree_level`, `field_of_study`) used by the final deployed model in `predictor.py`. This likely reflects normal refinement between the exploratory preprocessing stage and the final feature set selected for the production XGBoost model. It needs to be confirmed and reconciled once Likhitha's model-comparison write-up is in, so this section and the ML Recommendation Engine section describe the same final feature set consistently.
