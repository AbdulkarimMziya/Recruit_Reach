from django.conf import settings
from google import genai
from google.genai import types

from ..errors import AIServiceError
from .prompts import LENGTH_LIMITS, SYSTEM_PROMPT, build_prompt


def _call_ai(system_prompt: str, user_prompt: str) -> str:
    """
    Send one request to Gemini and return the reply text.
    The ONLY function that talks to Gemini.
    """
    # Read settings OUTSIDE the try: a missing setting is our bug and should
    # crash with its real error, not be reported as "service unavailable".
    api_key = settings.AI_API_KEY
    model = settings.AI_MODEL

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=20_000),  # milliseconds = 20 seconds
        )
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=400,
            ),
        )
    except Exception as e:
        raise AIServiceError("The AI service is unavailable. Please try again shortly.") from e

    text = (response.text or "").strip()
    if not text:
        raise AIServiceError("The AI returned an empty reply.")
    return text


def generate_message(resume_text, job_text, company, recruiter_name, message_type, tone) -> str:
    """Build the prompt, ask the AI, and make sure the message fits the length limit."""
    max_chars = LENGTH_LIMITS[message_type]
    prompt = build_prompt(resume_text, job_text, company, recruiter_name, message_type, tone)

    message = _call_ai(SYSTEM_PROMPT, prompt)

    if len(message) > max_chars:  # too long => ask once more, firmly
        message = _call_ai(
            SYSTEM_PROMPT,
            prompt + f"\n\nYour previous reply was too long. Keep it under {max_chars} characters.",
        )

    if len(message) > max_chars:  # still too long => give up
        raise AIServiceError("Couldn't write a short enough message. Please try again.")

    return message
