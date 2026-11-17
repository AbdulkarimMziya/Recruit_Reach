import hashlib

from django.core.cache import cache
from pydantic import ValidationError

from ..errors import AIServiceError
from ..schemas import ResumeData
from .generator import _call_ai
from .prompts import PARSE_PROMPT, PARSE_TEMPLATE

CACHE_VERSION = "v1"  # bump when PARSE_PROMPT changes, to retire old answers
CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours, in seconds
AI_TIMEOUT_S = 60  # a whole resume as JSON takes ~20 s; messages keep the 20 s default


def _cache_key(text: str) -> str:
    """The same text always gives the same key; any change gives a new one."""
    fingerprint = hashlib.sha256(text.encode()).hexdigest()
    return f"parse:{CACHE_VERSION}:{fingerprint}"


def parse_resume(text: str) -> ResumeData:
    """Sort resume text into sections, reusing a saved answer when we have one."""
    key = _cache_key(text)

    cached = cache.get(key)
    if cached is not None:  # hit: no Gemini call
        return ResumeData.model_validate(cached)

    # miss: ask the AI, then check its answer
    raw = _call_ai(
        PARSE_PROMPT,
        PARSE_TEMPLATE.format(resume_text=text),
        max_tokens=4000,
        schema=ResumeData,
        timeout_s=AI_TIMEOUT_S,
    )
    try:
        data = ResumeData.model_validate_json(raw)
    except ValidationError as e:
        raise AIServiceError("The AI's answer didn't match the resume format.") from e

    data = data.assign_ids()
    cache.set(key, data.model_dump(), timeout=CACHE_TIMEOUT)  # save only checked data
    return data
