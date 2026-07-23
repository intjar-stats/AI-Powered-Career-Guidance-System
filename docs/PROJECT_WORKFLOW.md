# Project Workflow

**AI-Powered Career Guidance System**
IDEAS-TIH (ISI) Internship Project
Mentor: Sandip Bhattacharyya | Organiser: Bidisha Dobe

This document outlines the phase-wise workflow followed during development, from initial research through to testing, deployment, and documentation. Each phase lists its objective, key activities, the team member(s) responsible, and the resulting deliverable.

---

## Phase 1: Research and Career Mapping

**Objective:** Establish the academic and data foundation for the system.

**Key Activities:**
- Reviewed existing literature on AI-based career guidance, skill-based career modelling, and generative AI in career counselling.
- Identified a suitable public dataset and defined the career-to-skill mapping structure.

**Owner(s):** Sama Jyothika (Literature Review), Aman Sawan P (Dataset & Career Mapping)

**Deliverables:** Literature review with cited references; sourced dataset with documented licensing; career-to-skill-gap, learning-path, and course-recommendation datasets.

---

## Phase 2: Data Preprocessing and Feature Engineering

**Objective:** Prepare a clean, model-ready dataset from the raw source data.

**Key Activities:**
- Verified the dataset for missing values and duplicate records.
- Engineered five derived features (Skill Score, Experience Level, GPA Category, Project Level, Certification Level).
- Applied label encoding to categorical fields and split the data into training and testing sets.

**Owner(s):** Uppala Lahari (Data Preprocessing)

**Deliverables:** Preprocessing notebook (`notebooks/Data_Preprocessing_Feature_Engineering__1_.ipynb`); processed training and testing datasets.

---

## Phase 3: Model Training and Career Recommendation

**Objective:** Build and validate the machine learning model that powers the Top-3 career recommendations.

**Key Activities:**
- Trained and compared four classification algorithms (KNN, Decision Tree, Random Forest, XGBoost) on the processed dataset using a multi-label, one-vs-rest approach.
- Selected XGBoost as the production model based on precision, recall, and F1 score.
- Exported the trained model, label binarizer, and input encoders for use by the application.

**Owner(s):** Bhupathi Likhitha (Project Lead, ML Recommendation Engine)

**Deliverables:** Training notebook (`notebooks/IntProjectISI.ipynb`); `career_model.pkl`, `label_binarizer.pkl`, `input_encoders.pkl`.

---

## Phase 4: Skill Gap Analysis and Learning Roadmap

**Objective:** Translate a recommended career into actionable, personalized guidance.

**Key Activities:**
- Built the logic to compare a student's self-rated skills against the requirements of their recommended career.
- Built the logic to generate a staged learning roadmap (priority skills, resources, duration, milestones) for the recommended career.

**Owner(s):** Ritik Gupta (Career Guidance & Roadmap Generation)

**Deliverables:** `recommender.py` (skill gap and learning path logic); supporting CSV datasets.

---

## Phase 5: Generative AI Integration

**Objective:** Add natural-language explanation and conversational guidance on top of the ML recommendations.

**Key Activities:**
- Integrated OpenRouter's OpenAI-compatible API to generate a personalized explanation of each recommendation.
- Implemented response validation, error handling, and a primary/fallback model configuration for resilience.

**Owner(s):** Amit Mondal (Generative AI Integration)

**Deliverables:** `gemini.py` (API integration, prompt construction, error handling).

---

## Phase 6: Frontend Development

**Objective:** Build the user-facing Streamlit application that ties every module together.

**Key Activities:**
- Built the profile input form, results display, and PDF report export.
- Following a mid-project team change (Section: Team Contributions), this phase's ownership and scope expanded to include a full dashboard-style visual layout, an AI Career Assistant chat interface, and a Resume Analysis module, each added in response to mentor feedback over the course of the project.

**Owner(s):** Md Intjar (Frontend, Testing, Deployment & Documentation)

**Deliverables:** `frontend/app.py`; `.streamlit/config.toml`.

---

## Phase 7: Testing, Deployment, and Documentation

**Objective:** Verify the system works correctly under real conditions, deploy it publicly, and document the entire process for evaluation.

**Key Activities:**
- Defined and executed a formal test plan covering core functionality, failure handling, and cross-device compatibility.
- Identified, root-caused, and resolved defects found during testing (see `tests/Testing_Plan.md`).
- Deployed and maintained the application on Streamlit Community Cloud, connected to the GitHub repository for continuous deployment.
- Authored the deployment guide, testing plan, and supporting sections of the final report.

**Owner(s):** Md Intjar (Testing, Deployment & Documentation)

**Deliverables:** `docs/Deployment_Guide.md`; `tests/Testing_Plan.md`; live deployed application; final report sections.

---

## Summary

| Phase | Focus Area | Primary Owner(s) |
|---|---|---|
| 1 | Research & Career Mapping | Jyothika, Aman |
| 2 | Data Preprocessing | Lahari |
| 3 | Model Training | Likhitha |
| 4 | Skill Gap & Roadmap Logic | Ritik |
| 5 | Generative AI Integration | Amit |
| 6 | Frontend Development | Intjar |
| 7 | Testing, Deployment & Documentation | Intjar |

Current status for each team member and deliverable is tracked separately in `docs/TEAM_STATUS.md`.
