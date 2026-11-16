from pydantic import ValidationError

from ..errors import AIServiceError
from ..schemas import ResumeData
from .generator import _call_ai
from .prompts import PARSE_PROMPT, PARSE_TEMPLATE


def parse_resume(text: str) -> ResumeData:
    """Ask the AI to sort resume text into sections, then check its answer."""
    raw = _call_ai(
        PARSE_PROMPT,
        PARSE_TEMPLATE.format(resume_text=text),
        max_tokens=4000,
        schema=ResumeData,
    )

    try:
        data = ResumeData.model_validate_json(raw)
    except ValidationError as e:
        raise AIServiceError("The AI's answer didn't match the resume format.") from e

    return data.assign_ids()
