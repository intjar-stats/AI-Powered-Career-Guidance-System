"""
gemini.py — GenAI explanation layer via OpenRouter.
 
NOTE: filename kept for now to avoid breaking existing imports across the repo,
but this does NOT call Google's Gemini API — it calls OpenRouter's OpenAI-
compatible endpoint. Recommend renaming to openrouter_client.py during final
repo cleanup (Task: Repository Organization) and updating the one import in app.py.
 
MODEL NOTE (updated during testing, July 2026): Third-party blog listicles
about "current free OpenRouter models" turned out to be unreliable — models
recommended there ("meta-llama/llama-3.3-70b-instruct:free",
"openai/gpt-oss-120b:free") returned 404s pointing to paid slugs when
actually tried. The only trustworthy source is OpenRouter's own live API
(https://openrouter.ai/api/v1/models — no key needed, filter for
pricing.prompt == "0"). Checked directly on 21 July 2026:
    - "nvidia/nemotron-3-ultra-550b-a55b:free" (the original primary model)
      IS confirmed free right now. Its earlier crash (a raw 'NoneType' is
      not subscriptable error) was most likely a transient/rate-limited
      response, not deprecation — now handled gracefully by the defensive
      check below instead of crashing.
    - Fallback switched to "cohere/north-mini-code:free" — confirmed free,
      and from a different provider than the primary, so a rate limit or
      outage on NVIDIA's free tier doesn't take down both models at once.
If this breaks again, re-check https://openrouter.ai/api/v1/models directly
rather than trusting a blog post — free-tier availability changes weekly.
"""
 
from openai import OpenAI, APIError, APITimeoutError
from config import OPENROUTER_API_KEY
 
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=20.0,  # seconds — prevents the app hanging indefinitely on a slow API
)
 
# Free-tier model can have availability issues under load — keep a fallback
# from a different provider. Verified free via OpenRouter's live API as of
# 21 July 2026 (see MODEL NOTE above).
PRIMARY_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
FALLBACK_MODEL = "cohere/north-mini-code:free"
 
 
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
