"""
gemini.py — GenAI explanation layer via OpenRouter.

NOTE: filename kept for now to avoid breaking existing imports across the repo,
but this does NOT call Google's Gemini API — it calls OpenRouter's OpenAI-
compatible endpoint. Recommend renaming to openrouter_client.py during final
repo cleanup (Task: Repository Organization) and updating the one import in app.py.
"""

from openai import OpenAI, APIError, APITimeoutError
from config import OPENROUTER_API_KEY

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=20.0,  # seconds — prevents the app hanging indefinitely on a slow API
)

# Free-tier model can have availability issues under load — keep a fallback
PRIMARY_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


class GenAIUnavailableError(RuntimeError):
    """Raised when both primary and fallback OpenRouter calls fail."""
    pass


def _call_model(model_name: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert AI Career Guidance Assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def get_career_recommendation(prompt: str) -> str:
    """
    Returns the GenAI-generated explanation text.
    Raises GenAIUnavailableError (never a raw exception) if both models fail —
    callers (app.py) should catch this and show a graceful message instead of
    letting the app crash.
    """
    try:
        return _call_model(PRIMARY_MODEL, prompt)
    except (APIError, APITimeoutError, Exception) as primary_error:  # noqa: BLE001
        try:
            return _call_model(FALLBACK_MODEL, prompt)
        except Exception as fallback_error:  # noqa: BLE001
            raise GenAIUnavailableError(
                f"Both primary and fallback models failed. "
                f"Primary: {primary_error} | Fallback: {fallback_error}"
            ) from fallback_error
