
"""
gemini.py — GenAI explanation layer via OpenRouter.
 
NOTE: filename kept for now to avoid breaking existing imports across the repo,
but this does NOT call Google's Gemini API — it calls OpenRouter's OpenAI-
compatible endpoint. Recommend renaming to openrouter_client.py during final
repo cleanup (Task: Repository Organization) and updating the one import in app.py.
 
MODEL NOTE (updated during testing, July 2026): OpenRouter's free-tier model
lineup changes frequently — models get moved to paid-only or renamed without
notice. Both models previously configured here had stopped working:
    - "nvidia/nemotron-3-ultra-550b-a55b:free" started returning a response
      with no `choices` (likely deprecated/renamed upstream), which crashed
      on `response.choices[0]` — this is now guarded against explicitly below.
    - "meta-llama/llama-3.1-8b-instruct:free" was discontinued on the free
      tier (OpenRouter returned a 404 pointing to the paid slug instead).
Replaced with two models verified free on OpenRouter as of July 2026. If this
breaks again in the future, check https://openrouter.ai/models (filter by
price = 0) for currently free models before assuming it's a code bug — this
has now happened twice and is a known characteristic of the free tier, not
an application defect.
"""
 
from openai import OpenAI, APIError, APITimeoutError
from config import OPENROUTER_API_KEY
 
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=20.0,  # seconds — prevents the app hanging indefinitely on a slow API
)
 
# Free-tier model can have availability issues under load — keep a fallback.
# Verified free on OpenRouter as of July 2026 (see MODEL NOTE above).
PRIMARY_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
FALLBACK_MODEL = "openai/gpt-oss-120b:free"
 
 
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
    # Defensive check: some providers occasionally return a 200-status
    # response with an error body instead of raising an HTTP error. In that
    # case response.choices can be None, and indexing it straight away
    # crashes with a confusing "'NoneType' object is not subscriptable"
    # error (seen during testing). Raise a clear, specific error instead so
    # it's obvious what went wrong if a model becomes unavailable again.
    if not response or not response.choices:
        raise ValueError(
            f"Model '{model_name}' returned no choices "
            f"(likely deprecated, renamed, or unavailable on OpenRouter)."
        )
    content = response.choices[0].message.content
    if not content:
        raise ValueError(f"Model '{model_name}' returned an empty response.")
    return content
 
 
def get_career_recommendation(prompt: str) -> str:
    """
    Returns the GenAI-generated explanation text.
    Raises GenAIUnavailableError (never a raw exception) if both models fail —
    callers (app.py) should catch this and show a graceful message instead of
    letting the app crash.
    """
    try:
        return _call_model(PRIMARY_MODEL, prompt)
    except Exception as primary_error:  # noqa: BLE001
        try:
            return _call_model(FALLBACK_MODEL, prompt)
        except Exception as fallback_error:  # noqa: BLE001
            raise GenAIUnavailableError(
                f"Both primary and fallback models failed. "
                f"Primary: {primary_error} | Fallback: {fallback_error}"
            ) from fallback_error
