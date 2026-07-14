# Testing Plan

**AI-Powered Career Guidance System**

| | |
|---|---|
| **Application Under Test** | https://ai-powered-career-guidance-system-blexmnd3bgujxy7b2u4uyl.streamlit.app |
| **Repository** | https://github.com/intjar-stats/AI-Powered-Career-Guidance-System |
| **Testing Approach** | Manual functional testing against the deployed application |
| **Test Environment** | Streamlit Community Cloud (production), Google Chrome on Windows |
| **Related Documents** | `docs/Deployment_Guide.md` (Section 3: Post-Deployment Verification) |

This document defines the testing strategy for the AI-Powered Career Guidance System, records the test cases executed against the live deployment, and logs the defects discovered and resolved during the testing phase. It supersedes the initial-phase `testing_checklist.md`.

---

## 1. Scope and Objectives

Testing focuses on verifying that the deployed application delivers its four core capabilities correctly and degrades gracefully under failure conditions:

1. **Career prediction** — the XGBoost model returns the top three career recommendations with confidence scores for a submitted user profile.
2. **Skill gap analysis and learning roadmap** — dataset-driven guidance sections populate correctly for matched profiles.
3. **Generative explanation** — the OpenRouter-backed AI Career Guidance module produces a personalized explanation, and the application remains fully usable when this external service is unavailable.
4. **Report export** — the PDF report generates, downloads, and renders completely.

**Out of scope:** model accuracy evaluation (covered in the model development documentation), load/performance testing, and security penetration testing. These are noted as future work in Section 5.

## 2. Testing Approach

Testing is performed manually against the production deployment rather than in an isolated environment. This choice reflects the project's architecture: the application is stateless, reads only bundled datasets and model artifacts, and its single external dependency (the OpenRouter API) can only be meaningfully exercised end-to-end.

Each test case specifies preconditions, steps, and an expected result. A test passes only when the actual behavior matches the expected result exactly; partial or degraded behavior is recorded as a defect (Section 4).

## 3. Test Cases and Results

### 3.1 Core Functionality

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-01 | Application availability | Open the live URL in a browser | Input form renders completely, no error banner | Pass |
| TC-02 | Profile submission | Fill all form fields with a representative profile and submit | Processing completes without a server error or crash | Pass |
| TC-03 | Top-3 career prediction | Inspect the recommendations section after TC-02 | Exactly three careers shown, each with a confidence percentage | Pass |
| TC-04 | Skill gap analysis | Inspect the Skill Gap Analysis section | Section populated with skills relevant to the predicted careers | Pass |
| TC-05 | Learning roadmap | Inspect the Learning Roadmap section | Learning stage, priority skills, learning path, resources, estimated duration, and milestone all populated | Pass |
| TC-06 | Generative explanation | Inspect the AI Career Guidance section | Personalized explanation text generated, including career narrative and action plan | Pass |
| TC-07 | PDF report export | Click "Download PDF Report"; open the downloaded file | PDF downloads and opens; contains recommendations, skill gaps, and roadmap; no missing glyphs or truncated text | Pass |

### 3.2 Failure Handling and Edge Cases

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-08 | Generative service unavailable | Submit a profile while the OpenRouter API rejects requests (observed during DEF-01, Section 4) | Application shows a clear notice that the AI explanation is temporarily unavailable, states that ML recommendations remain valid, and continues functioning — no crash | Pass |
| TC-09 | Unmatched profile | Submit a degree/field combination with no close match in the skill-gap and roadmap datasets | Graceful "no data found" message instead of an unhandled exception | Pass |
| TC-10 | Fallback model chain | Primary OpenRouter model unavailable | Application retries with the configured fallback model before surfacing an error | Pass (observed during DEF-01: both models were attempted) |

### 3.3 Pending Tests

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-11 | Cross-browser rendering | Repeat TC-01–TC-07 in a second browser (e.g. Edge or Firefox) | Identical behavior and layout | Pending |
| TC-12 | Mobile viewport | Open the live URL on a mobile device; run TC-02–TC-07 | All sections usable and readable on a narrow screen | Pending |
| TC-13 | Boundary inputs | Submit minimum and maximum values for numeric fields (e.g. CGPA, experience) | Predictions returned without errors; no nonsensical output | Pending |
| TC-14 | Repeated submissions | Submit several different profiles in one session | Each submission produces fresh results; no stale data carried over | Pending |

## 4. Defect Log

| ID | Description | Severity | Root Cause | Resolution | Status |
|---|---|---|---|---|---|
| DEF-01 | AI Career Guidance section returned HTTP 401 ("User not found") from the OpenRouter API for both primary and fallback models; ML-based sections remained functional via the designed fallback notice | Major | The configured API key had been revoked/disabled by the provider | Key rotation performed: a new API key was generated, updated in Streamlit Cloud's encrypted secrets manager, and verified against the live application; the old key was revoked. No code change was required, validating the externalized-credential design (see `docs/Deployment_Guide.md`, Section 5) | Resolved & verified |

## 5. Results Summary and Future Work

**Summary:** 10 of 14 defined test cases executed; all 10 passed. One major defect (DEF-01) was identified, diagnosed, resolved, and re-verified against the live deployment. Four test cases (TC-11–TC-14) remain pending and are scheduled before final submission.

**Future work (out of current scope):**

- Automated unit tests for `predictor.py`, `recommender.py`, and `data_loader.py` using `pytest`, enabling regression testing on future changes.
- Load testing to characterize behavior under concurrent users, relevant if the application moves beyond the free hosting tier.
- Systematic model evaluation (precision/recall per career class) as an extension of the model development work.
