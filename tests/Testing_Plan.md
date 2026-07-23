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

Our testing checks that the deployed application does seven things correctly, and that it fails safely when something goes wrong:

1. **Career prediction**: the XGBoost model gives the top three career recommendations with confidence scores for a submitted profile.
2. **Skill gap analysis and learning roadmap**: these sections fill in correctly from the datasets when a matching profile is given.
3. **AI explanation**: the AI Career Guidance module (through the OpenRouter API) generates a personalized explanation, and the app keeps working even when this external service is down.
4. **PDF report**: the report generates, downloads, and opens with complete content, including native visual charts matching the app.
5. **AI Career Assistant**: the chat module (added later, based on a mentor requirement) answers follow-up questions using the student's profile and recommendations, without disturbing the rest of the page.
6. **Dashboard visual summary**: an Overview section with donut charts, a bar chart, and a histogram, added after the mentor shared a reference dashboard design.
7. **Resume Analysis**: a second AI-powered module where a student uploads a resume (PDF) and receives a match score against their top recommended career, with strengths, gaps, and suggestions.

**Out of scope:** measuring model accuracy (that is part of the model development work), load testing with many users, and security testing. We list these under future work in Section 5.

## 2. Testing Approach

We tested manually on the live deployed app instead of a separate test setup. There is a simple reason for this: the app has no database or user accounts, its model files and datasets are packed inside the repository, and its only outside dependency is the OpenRouter API, which can only be properly tested by actually calling it. So testing on the live app checks the system exactly the way a real user would experience it.

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
| TC-16 | Personalized answers | Ask a follow-up question (for example, about certifications) | The answer uses the student's actual profile (degree, experience) and the recommended careers, not generic advice | Pass |
| TC-17 | Results stay on screen | After chatting and after downloading the PDF, scroll back up | Recommendations, skill gap, roadmap, and AI guidance are still visible | Pass |
| TC-18 | Chat when API is down | Send a chat message while the OpenRouter API is unavailable | Chat shows a clear "temporarily unavailable" notice; the results above are unaffected; no crash | Pending (needs an actual outage to test; the failure handling follows the same design already verified in TC-08) |

### 3.3 Failure Handling and Edge Cases

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-08 | AI service down | Submit a profile while the OpenRouter API rejects requests (this actually happened, see DEF-01 in Section 4) | App shows a clear notice that the AI explanation is temporarily unavailable, says the ML recommendations are still valid, and keeps working; no crash | Pass |
| TC-09 | Profile with no match | Submit a degree/field combination that has no close match in the skill-gap and roadmap datasets | A polite "no data found" message instead of a crash | Pass |
| TC-10 | Fallback model | Primary OpenRouter model unavailable | App tries the configured fallback model before showing an error | Pass (seen during DEF-01: both models were attempted) |

### 3.4 Extended Tests (completed with team participation)

These four tests were initially pending and were completed with help from team members testing the live app on their own devices, giving us genuine cross-device, cross-browser coverage.

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-11 | Second browser | Repeat TC-01 to TC-07 in another browser (Edge or Firefox) | Same behavior and layout | Pass (verified by a team member on laptop + Microsoft Edge; reported working with no issues) |
| TC-12 | Mobile screen | Open the live URL on a phone and run TC-02 to TC-07 | All sections usable and readable on a small screen | Pass (verified by a team member on iPhone + Safari; reported working with no issues) |
| TC-13 | Boundary inputs | Enter minimum and maximum values for number fields (GPA, experience) | Predictions come back without errors; output makes sense | Pass (GPA 0.0 and GPA 10.0 both returned sensible predictions and explanations, no errors) |
| TC-14 | Repeated submissions | Submit several different profiles one after another in the same session | Each submission gives fresh results; no old data left over | Pass (two contrasting profiles submitted back-to-back; the generated report header, AI explanation, and chat reset correctly on each new submission; no data from the earlier profile leaked into the later results) |

### 3.5 Observations and Findings (not application defects)

During TC-14, two deliberately contrasting profiles (an AI-degree profile with high ML skills, and a Cybersecurity-degree profile with low ML skills and high security/networking skills) produced the **same top-3 careers with 100% confidence for each**. We verified that the inputs were reaching the model correctly (the generated report header reflected each profile accurately), so this is a characteristic of the trained model rather than an application bug, possibly limited career-label diversity in the training data or a confidence-calibration issue. This observation has been flagged to the ML lead for review and is recorded here for transparency.

A second finding, of the same nature as DEF-02: we tested whether the "Gender" field could support a category beyond Male/Female by temporarily adding a third option and submitting it. The app correctly rejected it with a clear message: `Supported values: ['Female', 'Male']`. This confirms the training dataset itself only contains these two categories. This is not a bug, but a real limitation. We removed the test option, restored the original dropdown, and added a user-facing note (matching the field-of-study note) explaining that broader inclusivity is planned as future work requiring model retraining on a more representative dataset.

### 3.6 Dashboard, PDF Charts, Resume Analysis, and Navigation

These test cases cover features added after the mentor requested a dashboard-style visual layout (referencing an external tool's design) and a resume-analysis capability.

| ID | Test Case | Steps | Expected Result | Status |
|---|---|---|---|---|
| TC-19 | Dashboard Overview grid | Generate a recommendation, open the Overview section | Four charts render: a career-match donut, a skill-ratings bar chart, a skill-rating histogram, and a skill-readiness donut, each with distinct colors | Pass |
| TC-20 | PDF native visual charts | Download the PDF report and open it | The same four charts (donut/bar/histogram/donut) render inside the PDF itself, natively drawn rather than as screenshots, plus bordered "card" sections for the Roadmap and AI Guidance text | Pass (after several rounds of fixing text truncation and a duplicate profile summary; see DEF-04 and DEF-05) |
| TC-21 | Resume Analysis | Upload a PDF resume in the Resume Analysis section and click "Analyze Resume" | The AI returns a match score against the top recommended career, along with strengths, gaps, and improvement suggestions, referencing actual resume content | Pass |
| TC-22 | Section stays selected after an action | Open Resume Analysis, upload a resume, click "Analyze Resume" (or send a chat message in the Assistant section) | The app stays on the same section instead of jumping back to Overview | Pass (after fixing DEF-06; see defect log) |

## 4. Defect Log

| ID | Description | Severity | Root Cause | Resolution | Status |
|---|---|---|---|---|---|
| DEF-01 | The AI Career Guidance section returned HTTP 401 ("User not found") from the OpenRouter API for both the primary and fallback models. The ML-based sections kept working, and the app showed its designed fallback notice | Major | The API key stored in the deployment had been revoked/disabled on the provider's side | We rotated the key: generated a new API key, updated it in Streamlit Cloud's encrypted secrets manager, checked the live app end to end, and revoked the old key. No code change was needed. The credentials live outside the code, which is exactly why the fix was this simple (see `docs/Deployment_Guide.md`, Section 5) | Resolved & verified |
| DEF-02 | The "Field of Study" dropdown offered six options ("Computer Science", "Data Science", "Information Technology", "Electronics", "Mechanical", "Other"), but the ML model was trained on a different set of five values ("AI", "Computer Science", "Cybersecurity", "Data Science", "Software Engineering"). Selecting any of the four unsupported options gave a "Could not process your profile" error | Major | Mismatch between the form options in `app.py` and the category values the input encoders were trained on. This exact failure mode was anticipated in the troubleshooting table of `docs/Deployment_Guide.md` before it occurred | We updated the dropdown to list exactly the five values the model was trained on, and added a user-facing note explaining that other backgrounds (e.g. Economics, Statistics, Mathematics, Operations Research) would need model retraining and are planned as future work. Verified on the live app: every option now returns a prediction, and the error can no longer occur | Resolved & verified |
| DEF-03 | The AI Career Guidance section failed again after previously being fixed in DEF-01, this time with both the primary and fallback models returning 404 errors from OpenRouter | Major | The specific free-tier models configured had been discontinued. Our first fix attempt (based on a third-party blog's list of "currently free" models) also failed immediately, since that list turned out to be stale | We stopped trusting secondary sources and queried OpenRouter's own live API (`https://openrouter.ai/api/v1/models`) directly, filtering for models with zero listed price. Reconfigured the primary and fallback models to two verified-free models from different providers (so a single provider's outage or rate limit doesn't take down both). Also added a defensive check in `gemini.py` so that if a model ever returns a malformed response again, the app shows a clear diagnostic message instead of a confusing crash-like error | Resolved & verified |
| DEF-04 | Text was getting cut off in the PDF report. Most visibly, career names were truncated (e.g. "Business Intelligence Analyst" showed as "...Analys") and paragraph text sometimes stopped mid-sentence, especially inside the new bordered card sections | Major | The PDF's text-wrapping used a fixed character-count estimate to decide where to break lines, which doesn't account for actual proportional font widths (some letters are much wider than others). This became visible once the card layout narrowed the available width | Replaced the character-count estimate with fpdf2's own `get_string_width()`, which measures real rendered width for the current font, and rewrote the wrapping logic to use it throughout the PDF (`_write()` and the new markdown renderer). Verified with multiple test PDFs including long career names and long AI-generated text | Resolved & verified |
| DEF-05 | The AI-generated explanation sometimes repeated the student's profile summary (name, age, degree, GPA) at the very start of its response, duplicating the "Profile Summary" section that already appears above it in both the app and the PDF | Minor | A common LLM habit (restating context before answering) rather than an application bug | Added an explicit instruction in the prompt telling the model not to restate the profile, since it is already shown separately. (This depends on the model reliably following instructions; if it recurs, a text-level safeguard is a documented next step.) | Resolved & verified |
| DEF-06 | After adding the Resume Analysis and dashboard sections as tabs, clicking "Analyze Resume" (or any button inside a non-first tab) caused the page to jump back to the "Overview" tab instead of staying put, even though the action itself completed correctly | Major | Streamlit's `st.tabs()` does not remember which tab was active across a script rerun, and any button click triggers a full rerun. This is a known Streamlit limitation, not something specific to our code | Replaced `st.tabs()` with a manual section switcher (`st.radio`, later constrained with a small CSS override to stay on one line) tied to `st.session_state` via its `key`, which does persist correctly across reruns. Verified: switching sections, then triggering an action inside one (resume analysis, chat), no longer resets the view | Resolved & verified |
| DEF-07 | The Skill Gap Analysis showed the same gap percentage (48%) and the same estimated hours for every student who received the same top recommended career, regardless of their own skill ratings | Major | The original `get_skill_gap()` function looked up a single fixed row from the `career_skill_gap.csv` file for the target career, using pre-computed `Gap_Percentage` and `Estimated_Hours` columns that were the same for everyone rather than being calculated from the student's own profile | Rithik rewrote this as `compute_skill_gap(profile, target_career)`, which reads the required skills for the career from the CSV but compares each one against the student's own slider ratings from their submitted profile, computing the gap percentage and estimated hours individually per student. Verified on the live app: two profiles with different skill ratings for the same recommended career now produce different, profile-specific results (e.g. 66.7% gap and 120 estimated hours for one tested profile), instead of a fixed 48% for everyone. One related limitation was found during this fix: a handful of required skills named in the CSV (e.g. "TensorFlow", "DSA", "Statistics") don't correspond to any of the 16 skills the application's form actually collects, so these are treated as a gap by default regardless of the student's real proficiency. This is noted as a known limitation rather than fixed, since addressing it would mean adding new form fields, which is out of scope this close to submission | Resolved & verified |

## 5. Results Summary and Future Work

**Summary:** We have run 21 of the 22 defined test cases, and all 21 passed. The only remaining case (TC-18, chat behavior during an API outage) follows an already-verified failure-handling design and can only be exercised during an actual outage. Testing included cross-device and cross-browser verification carried out by team members on their own devices (Chrome/Windows, Edge/laptop, Safari/iPhone). Seven defects were found, fixed, and re-checked on the live app across the project: a revoked API key (DEF-01), a form/model category mismatch (DEF-02), an OpenRouter model deprecation (DEF-03), PDF text-wrapping and formatting issues (DEF-04, DEF-05), a Streamlit tab-persistence bug (DEF-06), and a skill gap calculation that was not personalized to the student (DEF-07). Testing also produced two findings passed on for review rather than fixed as defects: a model-confidence observation (Section 3.5) and a confirmed dataset limitation on the Gender field, which is now documented in the app itself. The AI Career Assistant chat, the dashboard visual summary, and the Resume Analysis module were each added mid-project in response to mentor feedback and tested on the live app on the day each was released.

**Future work (outside the current scope):**

- Automated unit tests for `predictor.py`, `recommender.py`, and `data_loader.py` using `pytest`, so that future code changes can be checked automatically.
- Load testing to see how the app behaves with many users at once, useful if the project ever moves beyond the free hosting tier.
- A proper statistical evaluation of the model (precision/recall for each career class), as an extension of the model development work.
- Model retraining on a more diverse dataset to support additional Field of Study and Gender categories beyond what the current training data covers.
- Extending the PDF report to include the Resume Analysis results (currently available in the app only).
