"""
config.py — loads OPENROUTER_API_KEY from either:
  - Streamlit Cloud's secrets manager (st.secrets), for deployment, or
  - a local .env file (via python-dotenv), for local development

Does NOT crash the app at import time if the key is missing — app.py checks
and shows a clear on-screen error instead, so the rest of the app (form, etc.)
can still be inspected during development/testing.
"""

import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# On Streamlit Cloud, secrets are set via the app's Settings > Secrets panel
# and exposed through st.secrets, not automatically as OS environment variables.
try:
    import streamlit as st
    if not OPENROUTER_API_KEY and "OPENROUTER_API_KEY" in st.secrets:
        OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    pass  # not running inside Streamlit, or secrets not configured — fine locally
