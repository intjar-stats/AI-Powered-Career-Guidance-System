# Testing Plan

**AI-Powered Career Guidance System**

| | |
|---|---|
| **Application Under Test** | https://ai-powered-career-guidance-system-blexmnd3bgujxy7b2u4uyl.streamlit.app |
| **Repository** | https://github.com/intjar-stats/AI-Powered-Career-Guidance-System |
| **Testing Approach** | Manual functional testing on the deployed application |
| **Test Environment** | Streamlit Community Cloud (production), Google Chrome on Windows |
| **Related Documents** | `docs/Deployment_Guide.md` (Section 3: Post-Deployment Verification) |

This document describes how we tested the AI-Powered Career Guidance System. It lists the test cases we ran on the live application, their results, and the defects we found and fixed along the way. It replaces the earlier `testing_checklist.md`, which was made in the initial phase of the project.

---

## 1. Scope and Objectives

Our testing checks that the deployed application does five things correctly, and that it fails safely when something goes wrong:

1. **Career prediction** — the XGBoost model gives the top three career recommendations with confidence scores for a submitted profile.
2. **Skill gap analysis and learning roadmap** — these sections fill in correctly from the datasets when a matching profile is given.
3. **AI explanation** — the AI Career Guidance module (through the OpenRouter API) generates a personalized explanation, and the app keeps working even when this external service is down.
4. **PDF report** — the report generates, downloads, and opens with complete content.
5. **AI Career Assistant** — the chat module (added later, based on a mentor requirement) answers follow-up questions using the student's profile and recommendations, without disturbing the rest of the page.

**Out of scope:** measuring model accuracy (that is part of the model development work), load testing with many users, and security testing. We list these under future work in Section 5.

## 2. Testing Approach

We tested manually on the live deployed app instead of a separate test setup. There is a simple reason for this: the app has no database or user accounts, its model files and datasets are packed inside the repository, and its only outside dependency is the OpenRouter API — which can only be properly tested by actually calling it. So testing on the live app checks the system exactly the way a real user would experience it.

Every test case below has clear steps and an expected result. We mark a test as Pass only when the app behaves exactly as expected. Anything less goes into the defect log (Section 4).

## 3. Test Cases and Results

### 3.1 Core Functionality

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-01 | App opens | Open the live URL in a browser | Input form loads fully, no error banner | Pass |
| TC-02 | Profile submission | Fill all form fields with a realistic profile and submit | Processing completes without any server error or crash | Pass |
| TC-03 | Top-3 prediction | Check the recommendations after TC-02 | Exactly three careers shown, each with a confidence percentage | Pass |
| TC-04 | Skill gap analysis | Check the Skill Gap Analysis section | Section filled with skills related to the predicted careers | Pass |
| TC-05 | Learning roadmap | Check the Learning Roadmap section | Learning stage, priority skills, learning path, resources, duration, and milestone all filled | Pass |
| TC-06 | AI explanation | Check the AI Career Guidance section | Personalized explanation generated, with career details and an action plan | Pass |
| TC-07 | PDF download | Click "Download PDF Report" and open the file | PDF downloads and opens; has recommendations, skill gaps, and roadmap; no broken characters or cut text | Pass |

### 3.2 AI Career Assistant (Interactive Chat)

We added these test cases when the chat module was introduced (a mentor requirement that came during the project). We ran them on the live app on the same day the feature went live.

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-15 | Chat section appears | Generate a recommendation and scroll below the PDF button | "AI Career Assistant" section appears with a chat input box | Pass |
| TC-16 | Personalized answers | Ask a follow-up question (for example, about certifications) | The answer uses the student's actual profile (degree, experience) and the recommended careers — not generic advice | Pass |
| TC-17 | Results stay on screen | After chatting and after downloading the PDF, scroll back up | Recommendations, skill gap, roadmap, and AI guidance are still visible | Pass |
| TC-18 | Chat when API is down | Send a chat message while the OpenRouter API is unavailable | Chat shows a clear "temporarily unavailable" notice; the results above are unaffected; no crash | Pending (needs an actual outage to test; the failure handling follows the same design already verified in TC-08) |

### 3.3 Failure Handling and Edge Cases

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-08 | AI service down | Submit a profile while the OpenRouter API rejects requests (this actually happened — see DEF-01 in Section 4) | App shows a clear notice that the AI explanation is temporarily unavailable, says the ML recommendations are still valid, and keeps working — no crash | Pass |
| TC-09 | Profile with no match | Submit a degree/field combination that has no close match in the skill-gap and roadmap datasets | A polite "no data found" message instead of a crash | Pass |
| TC-10 | Fallback model | Primary OpenRouter model unavailable | App tries the configured fallback model before showing an error | Pass (seen during DEF-01: both models were attempted) |

### 3.4 Extended Tests (completed with team participation)

These four tests were initially pending and were completed with help from team members testing the live app on their own devices — giving us genuine cross-device, cross-browser coverage.

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-11 | Second browser | Repeat TC-01 to TC-07 in another browser (Edge or Firefox) | Same behavior and layout | Pass (verified by a team member on laptop + Microsoft Edge; reported working with no issues) |
| TC-12 | Mobile screen | Open the live URL on a phone and run TC-02 to TC-07 | All sections usable and readable on a small screen | Pass (verified by a team member on iPhone + Safari; reported working with no issues) |
| TC-13 | Boundary inputs | Enter minimum and maximum values for number fields (GPA, experience) | Predictions come back without errors; output makes sense | Pass (GPA 0.0 and GPA 10.0 both returned sensible predictions and explanations, no errors) |
| TC-14 | Repeated submissions | Submit several different profiles one after another in the same session | Each submission gives fresh results; no old data left over | Pass (two contrasting profiles submitted back-to-back; the generated report header, AI explanation, and chat reset correctly on each new submission; no data from the earlier profile leaked into the later results) |

### 3.5 Observation for the ML Team (not an application defect)

During TC-14, two deliberately contrasting profiles (an AI-degree profile with high ML skills, and a Cybersecurity-degree profile with low ML skills and high security/networking skills) produced the **same top-3 careers with 100% confidence for each**. We verified that the inputs were reaching the model correctly (the generated report header reflected each profile accurately), so this is a characteristic of the trained model rather than an application bug — possibly limited career-label diversity in the training data or a confidence-calibration issue. This observation has been flagged to the ML lead for review and is recorded here for transparency.

## 4. Defect Log

| ID | Description | Severity | Root Cause | Resolution | Status |
|---|---|---|---|---|---|
| DEF-01 | The AI Career Guidance section returned HTTP 401 ("User not found") from the OpenRouter API for both the primary and fallback models. The ML-based sections kept working, and the app showed its designed fallback notice | Major | The API key stored in the deployment had been revoked/disabled on the provider's side | We rotated the key: generated a new API key, updated it in Streamlit Cloud's encrypted secrets manager, checked the live app end to end, and revoked the old key. No code change was needed — the credentials live outside the code, which is exactly why the fix was this simple (see `docs/Deployment_Guide.md`, Section 5) | Resolved & verified |
| DEF-02 | The "Field of Study" dropdown offered six options ("Computer Science", "Data Science", "Information Technology", "Electronics", "Mechanical", "Other"), but the ML model was trained on a different set of five values ("AI", "Computer Science", "Cybersecurity", "Data Science", "Software Engineering"). Selecting any of the four unsupported options gave a "Could not process your profile" error | Major | Mismatch between the form options in `app.py` and the category values the input encoders were trained on. This exact failure mode was anticipated in the troubleshooting table of `docs/Deployment_Guide.md` before it occurred | We updated the dropdown to list exactly the five values the model was trained on, and added a user-facing note explaining that other backgrounds (e.g. Economics, Statistics, Mathematics, Operations Research) would need model retraining and are planned as future work. Verified on the live app: every option now returns a prediction, and the error can no longer occur | Resolved & verified |

## 5. Results Summary and Future Work

**Summary:** We have run 17 of the 18 defined test cases, and all 17 passed. The only remaining case (TC-18, chat behavior during an API outage) follows an already-verified failure-handling design and can only be exercised during an actual outage. Testing included cross-device and cross-browser verification carried out by team members on their own devices (Chrome/Windows, Edge/laptop, Safari/iPhone). Two major defects were found, fixed, and re-checked on the live app: DEF-01 (a revoked API key, solved by key rotation with no code change) and DEF-02 (a mismatch between the form's field-of-study options and the model's training values, solved by aligning the form with the model). Notably, DEF-02 was a failure mode we had already predicted in the deployment guide's troubleshooting table before it occurred. Testing also produced one model-level observation (Section 3.5) that has been passed to the ML lead. The AI Career Assistant chat module, added mid-project after a mentor requirement, was tested on the live app on the day it was released (TC-15 to TC-17).

**Future work (outside the current scope):**

- Automated unit tests for `predictor.py`, `recommender.py`, and `data_loader.py` using `pytest`, so that future code changes can be checked automatically.
- Load testing to see how the app behaves with many users at once — useful if the project ever moves beyond the free hosting tier.
- A proper statistical evaluation of the model (precision/recall for each career class), as an extension of the model development work.
