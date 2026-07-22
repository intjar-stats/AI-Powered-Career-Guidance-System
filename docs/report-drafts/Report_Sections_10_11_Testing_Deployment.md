# Final Report — Draft Sections (Testing & Deployment)

> **Status:** Draft for review. Section numbers follow the proposed report outline
> (Testing = Section 10, Deployment = Section 11) and may change once the outline
> is approved by the project lead. To be merged into the final report document.

---

## 10. Testing and Quality Assurance

### 10.1 Testing Strategy

We tested the system manually, end to end, on the deployed application itself. This was a deliberate choice, not a shortcut. The application has no database or user accounts, its trained model files and datasets are packed inside the repository, and its only external dependency is the OpenRouter API used by the AI guidance module — and the only real way to test an external API is to actually call it. Testing on the live deployment therefore checked the system exactly the way an end user experiences it.

We prepared a formal testing plan, which is kept in the project repository (`tests/Testing_Plan.md`). It defines twenty-two test cases across six groups: core functionality, the AI Career Assistant chat, failure handling and edge cases, extended compatibility checks, the dashboard visual summary and Resume Analysis module (both added later in response to mentor feedback), and a set of observations passed on for review rather than treated as defects. Each test case has clear steps and an expected result, and we count a test as passing only when the app behaves exactly as expected.

### 10.2 Coverage and Results

The core functionality tests covered the complete user journey: opening the app and filling the form, getting the top three career recommendations with confidence scores, checking the skill gap analysis and learning roadmap sections, reading the AI-generated career guidance, and downloading the results as a PDF report. All core test cases passed on the live deployment.

We paid special attention to what happens when things go wrong. The system is designed to degrade gracefully when the external AI service is unavailable: the page shows a clear notice that the AI explanation is temporarily unavailable, tells the user that the ML-based recommendations are still valid, and keeps working normally. We did not just design this behavior — we actually saw it work under a real failure, described in Section 10.3. We also confirmed that a profile with no close match in the skill-gap and roadmap datasets produces a polite "no data found" message instead of a crash. Exploratory testing on the live app also uncovered a second defect — unsupported options in the field-of-study dropdown — which is likewise described in Section 10.3.

Testing also had to adapt to a change in requirements. Midway through the project, our mentor asked for an interactive AI assistant in the app, and later for a more visual, dashboard-style layout (referencing an external tool's design) and a resume-analysis capability. Each time a feature was built and released, we defined new test cases and ran them on the live app the same day: the chat module's responses use the student's actual profile rather than generic advice; the dashboard's four charts (a career-match donut, a skill-ratings bar chart, a skill-rating histogram, and a skill-readiness donut) render correctly with distinct colors, both in the app and — natively drawn, not as image screenshots — inside the downloadable PDF; and the Resume Analysis module correctly extracts text from an uploaded PDF resume and returns an AI-generated match score, strengths, gaps, and suggestions against the student's top recommended career.

At the time of writing, we have run twenty-one of the twenty-two defined test cases, and all twenty-one passed. The only remaining case — chat behavior during an API outage — follows the same failure-handling design we already verified, and can only be truly exercised during an actual outage.

### 10.3 Defects Discovered and Resolved

Across the project, we found and resolved six defects. Grouped by theme, they show a consistent pattern: the failures were almost always in configuration or presentation, never in the core prediction logic, and the system's designed fallback behavior worked correctly every time something failed.

**External service failures.** Twice during the project, the AI Career Guidance module stopped working because of the OpenRouter API rather than our own code. The first time, the configured API key had been revoked on the provider's side (HTTP 401); the fix was a straightforward key rotation with no code change, since credentials are kept entirely outside the codebase by design (Section 11.3). The second time, both the primary and fallback language models had been discontinued on the free tier (HTTP 404) — and notably, a third-party blog's list of "currently free" models turned out to be stale and led us to the wrong replacement models on the first attempt. We corrected this by querying OpenRouter's own live API directly for models with zero listed price, and chose a primary and fallback model from two different providers, so that one provider's outage doesn't take down both. In both incidents, users continued to receive their complete ML-based recommendations along with a clear "temporarily unavailable" notice — the graceful-degradation design worked exactly as intended under real failures, not just in theory.

**Form-to-model mismatches.** The "Field of Study" dropdown originally offered options the trained model had never seen, producing a "could not process your profile" error on four of six choices — a mismatch we had actually anticipated in the deployment guide's troubleshooting table before it occurred. We aligned the dropdown with the model's five actual training categories and added a note about the limitation. A related check on the "Gender" field, run the same way, confirmed the training dataset only contains Male/Female — not a defect, but a real dataset limitation now documented in the app and listed as future work (broader categories would require retraining on a more representative dataset).

**Presentation-layer issues in the PDF report.** Adding native, hand-drawn charts and bordered "card" sections to the PDF (to visually match the app's dashboard, per mentor feedback) surfaced two formatting bugs: text was getting cut off in places, and the AI's response sometimes repeated the profile summary that already appears above it. The truncation traced back to estimating line-wrap points from a fixed character count, which doesn't account for actual proportional font widths — replacing that estimate with fpdf2's own string-width measurement fixed it throughout the report. The duplicate profile summary was a common LLM habit (restating context before answering) rather than a code defect, resolved with an explicit prompt instruction.

**A Streamlit-specific UI bug.** After adding the Resume Analysis and dashboard sections as tabs, clicking any button inside a non-first tab (such as "Analyze Resume") caused the page to visibly jump back to the first tab, even though the action itself had completed correctly. This turned out to be a known Streamlit limitation — `st.tabs()` doesn't remember which tab was active across a script rerun, and any button click triggers a full rerun. We replaced it with a manual section switcher backed by `st.session_state`, which does persist correctly.

All six defects, their root causes, and their resolutions are recorded in the defect log of the testing plan.

### 10.4 Limitations of the Testing Approach

Our testing was limited to functional checks. We did not write automated unit tests for the individual Python modules, did not do load testing with many simultaneous users, and did not do a statistical evaluation of the model's quality. These were conscious scoping decisions given the project timeline, and we discuss them as future work in Section 13.

---

## 11. Deployment

### 11.1 Platform Selection

The application is deployed on Streamlit Community Cloud. We chose this platform for three reasons. First, it supports Streamlit apps natively, so there was no need to set up servers or containers. Second, it connects directly to GitHub: every push to the `main` branch of the repository is picked up and redeployed automatically, which gave us a simple continuous deployment workflow with no extra infrastructure. Third, the free tier is enough for an internship project demo, and it gives a stable public URL that anyone can open.

### 11.2 Deployment Architecture and Process

The deployed app runs straight from the project's public GitHub repository, with `frontend/app.py` as the entry point. On every deployment, the platform clones the repository, installs the packages listed in the root-level `requirements.txt` (including Scikit-Learn, XGBoost, Streamlit, the PDF-generation library, and — added later for the Resume Analysis feature — a pure-Python PDF text-extraction library with no system-level dependencies, kept lightweight for the same reason), and starts the app. The trained model files (`career_model.pkl`, `input_encoders.pkl`, `label_binarizer.pkl`) and the four supporting CSV datasets travel inside the repository, so the deployed app is fully self-contained except for one external service.

That one external service is the OpenRouter API, which powers both the AI career guidance explanation and the AI Career Assistant chat. The module is set up with a primary and a fallback language model, so that if the primary model is busy or unavailable, the app tries the fallback before giving up.

The complete deployment procedure — prerequisites, configuration values, and a troubleshooting table built from problems we actually faced — is written up in `docs/Deployment_Guide.md` in the repository. Any team member can redeploy the application on their own by following it.

### 11.3 Security and Credential Management

Since the repository is public, we were careful with credentials from the start. The OpenRouter API key is never committed to version control in any form. During local development, it is read from a `.env` file that Git ignores (a `.env.example` template in the repository shows the expected format without the real value). In production, the key is supplied through Streamlit Cloud's encrypted secrets manager and read via `st.secrets`. The configuration module checks both places, so the same code runs locally and in production without changes.

This design paid off in a very concrete way during the project. When the original API key was revoked by the provider (the defect described in Section 10.3), recovery took only a few minutes: generate a new key, update the deployment secret, done. No code was touched, nothing was committed, and the platform restarted the app on its own.

### 11.4 Post-Deployment Verification

We did not treat a successful build as a finished deployment. After going live, we ran a defined smoke-test sequence on the live URL: submitting a profile, checking the recommendations, the skill gap and roadmap sections, the AI explanation, the chat assistant, and the PDF download, and confirming that an unmatched profile is handled politely. This sequence is written down in both the deployment guide and the testing plan, and we repeat it after every significant push to `main` — because every such push automatically becomes the new live version.

The application is live at:
**https://ai-powered-career-guidance-system-blexmnd3bgujxy7b2u4uyl.streamlit.app**
