# Deployment Guide

**AI-Powered Career Guidance System**

| | |
|---|---|
| **Deployment Platform** | Streamlit Community Cloud (free tier) |
| **Repository** | https://github.com/intjar-stats/AI-Powered-Career-Guidance-System |
| **Live Application** | https://ai-powered-career-guidance-system-blexmnd3bgujxy7b2u4uyl.streamlit.app |
| **Application Entry Point** | `frontend/app.py` |
| **Branch Deployed** | `main` |

This document describes the procedure followed to deploy the application from the GitHub repository to a publicly accessible URL, along with post-deployment verification steps and resolutions for issues encountered during the process. It is intended both as a record of the deployment carried out for this project and as a reference for redeploying the application in the future.

---

## 1. Pre-Deployment Checklist

The following conditions were verified before initiating deployment:

- [x] The GitHub repository is up to date, with `frontend/`, `data/`, and `requirements.txt` pushed to the `main` branch.
- [x] All three serialized model artifacts are present in `frontend/`: `career_model.pkl`, `label_binarizer.pkl`, and `input_encoders.pkl`.
- [x] `requirements.txt` is located at the repository **root** (Streamlit Cloud reads it from this location).
- [x] The local `.env` file is excluded from version control via `.gitignore`. No API credentials appear anywhere in the repository.
- [x] A valid OpenRouter API key is available for configuration as a deployment secret.

---

## 2. Deployment Procedure

### 2.1 Platform Account Setup

1. Navigate to https://share.streamlit.io.
2. Sign in using the GitHub account that owns the repository (`intjar-stats`).
3. Authorize Streamlit Community Cloud to access the account's repositories when prompted.

### 2.2 Application Configuration

1. Select **Create app** → **Deploy a public app from GitHub**.
2. Provide the following configuration:

   | Field | Value |
   |---|---|
   | Repository | `intjar-stats/AI-Powered-Career-Guidance-System` |
   | Branch | `main` |
   | Main file path | `frontend/app.py` |

3. Open **Advanced settings** before deploying, in order to configure the API secret described in Section 2.3.

### 2.3 Secret Management

The application requires an OpenRouter API key at runtime for the generative-AI explanation module. In line with standard security practice, this key is **never committed to the repository**. It is instead supplied through Streamlit Cloud's encrypted secrets manager.

1. In *Advanced settings* (or later via *App settings → Secrets*), add the key in TOML format:

   ```toml
   OPENROUTER_API_KEY = "<actual key>"
   ```

2. Save the configuration.

The application's configuration module (`frontend/config.py`) resolves the key in two stages: it first checks the process environment (populated from a local `.env` file during development), and falls back to `st.secrets` when running on Streamlit Cloud. This allows the same codebase to run locally and in production without modification.

### 2.4 Build and Launch

Selecting **Deploy** triggers the platform's build pipeline, which:

1. clones the repository,
2. installs all dependencies listed in `requirements.txt`, and
3. launches `frontend/app.py`.

Build progress and any errors are reported in the platform's log panel. Errors encountered during this project's deployment, together with their resolutions, are documented in Section 4.

---

## 3. Post-Deployment Verification

The following verification sequence was executed against the live URL before the deployment was considered complete.

| # | Test | Expected Result | Status |
|---|---|---|---|
| 1 | Load the application URL | Input form renders without errors | Pass |
| 2 | Submit a representative user profile | Response returned without server error | Pass |
| 3 | Inspect prediction output | Top-3 career recommendations displayed with confidence scores | Pass |
| 4 | Inspect analysis sections | Skill Gap Analysis and Learning Roadmap populated correctly | Pass |
| 5 | Inspect generative module | AI Career Guidance explanation generated (confirms the API secret is functioning) | Pass |
| 6 | Edge case: profile with no close match in the skill-gap/roadmap datasets | Application displays a graceful "no data found" message rather than crashing | Pass |
| 7 | Report export | PDF report downloads and opens with complete, correctly rendered content | Pass |

Any failure at step 6 (an unhandled crash on unmatched input) is treated as a defect to be logged and resolved prior to final submission, not deferred.

---

## 4. Troubleshooting Reference

The table below records failure modes relevant to this deployment, including issues actually encountered and their resolutions.

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `ModuleNotFoundError` during build (e.g. `xgboost`) | Package missing from `requirements.txt`, or the file was not detected | Confirm `requirements.txt` exists at the repository root, not inside `frontend/` |
| `FileNotFoundError: career_model.pkl` | Model artifacts absent or misplaced | Confirm all three `.pkl` files reside in `frontend/`, alongside `app.py` |
| `FileNotFoundError` on a CSV file | Datasets absent or misplaced | Confirm all four CSV files reside in `data/` at the repository root |
| Application loads, but the generative explanation fails or shows a warning | Secret misconfigured | Verify *Settings → Secrets*; the key name must be exactly `OPENROUTER_API_KEY` |
| HTTP 401 ("User not found") from the OpenRouter API despite a configured secret | The stored key has been revoked or disabled by the provider | Generate a new key, revoke the old one, and update the value in *Settings → Secrets*; the application restarts automatically |
| Crash on `st.secrets["OPENROUTER_API_KEY"]` | Secret not configured at all | Add the secret as described in Section 2.3 |
| Build succeeds, but predictions fail with a `ValueError` on an unrecognized category | Form options diverge from the categories the input encoders were trained on | Cross-check the dropdown options in `app.py` against the training-time category values used by `input_encoders.pkl` |

---

## 5. Security Considerations

- **Credential isolation.** The OpenRouter API key is stored exclusively in Streamlit Cloud's encrypted secrets manager and in an untracked local `.env` file. At no point does the key appear in the repository, its commit history, or any project documentation.
- **Key rotation.** During the project, the original API key was found to be invalid (rejected by the provider). It was replaced through a rotation procedure: generating a new key, updating the deployment secret, verifying the live application, and revoking the old key, all without any change to the codebase. This validated the design decision to externalize credentials from the code.
- **Public repository hygiene.** Because the repository is public, `.gitignore` rules and the `.env.example` template are used to ensure contributors can configure the application locally without ever committing real credentials.

---

## 6. Redeployment Notes

- Pushes to the `main` branch are picked up automatically by Streamlit Community Cloud; no manual redeployment step is required for code changes.
- Changes to secrets take effect after saving in the *Secrets* panel, which triggers an automatic application restart (typically within one to two minutes).
- If the application is ever migrated to a different Streamlit account or platform, Sections 2.1–2.3 must be repeated in full, and the live URL recorded in this document and in the final report must be updated.
