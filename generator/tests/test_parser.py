import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from generator.errors import AIServiceError
from generator.schemas import ResumeData
from generator.services.generator import types
from generator.services.parser import AI_TIMEOUT_S, parse_resume
from generator.services.prompts import PARSE_PROMPT

RESUME_TEXT = "Sam Lee\nDev Co-op, Acme\n- Built an API\nRecruitReach\n- Django REST API"


def sorted_resume():
    """What a good answer from Gemini looks like, as a dict."""
    return {
        "name": "Sam Lee",
        "experience": [{"title": "Dev Co-op", "organisation": "Acme", "bullets": ["Built an API"]}],
        "projects": [{"title": "RecruitReach", "bullets": ["Django REST API"]}],
        "education": [],
        "skills": ["Python"],
        "certifications": [],
    }


def ai_replies(fake_gemini, text):
    """Make the fake Gemini answer with this text."""
    fake_gemini.return_value = SimpleNamespace(text=text)


# ---------- a good answer ----------


def test_good_answer_becomes_resume_data_with_ids(fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    data = parse_resume(RESUME_TEXT)

    assert isinstance(data, ResumeData)
    assert data.experience[0].organisation == "Acme"
    assert data.experience[0].id == "exp-1"
    assert data.projects[0].id == "proj-1"


def test_asks_gemini_for_json_in_the_resume_shape(fake_gemini):
    """The bit that matters most: JSON mode is really switched on."""
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    parse_resume(RESUME_TEXT)

    config = fake_gemini.call_args.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is ResumeData
    assert config.max_output_tokens == 4000
    assert config.system_instruction == PARSE_PROMPT


def test_parsing_gets_a_longer_timeout_than_messages(fake_gemini):
    """A whole resume as JSON takes ~20 s, so parsing must not use the 20 s default."""
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    with patch.object(types, "HttpOptions", wraps=types.HttpOptions) as http_options:
        parse_resume(RESUME_TEXT)

    assert http_options.call_args.kwargs["timeout"] == AI_TIMEOUT_S * 1000
    assert AI_TIMEOUT_S > 20


def test_resume_text_is_sent_inside_resume_tags(fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    parse_resume(RESUME_TEXT)

    sent = fake_gemini.call_args.kwargs["contents"]
    assert f"<resume>\n{RESUME_TEXT}\n</resume>" in sent


# ---------- bad answers ----------


def test_answer_missing_a_section_raises_ai_service_error(fake_gemini):
    answer = sorted_resume()
    del answer["projects"]
    ai_replies(fake_gemini, json.dumps(answer))

    with pytest.raises(AIServiceError, match="didn't match the resume format"):
        parse_resume(RESUME_TEXT)


@pytest.mark.parametrize("reply", ["Sorry, I can't do that.", '{"name": "Sam"', "[]"])
def test_answer_that_is_not_resume_json_raises_ai_service_error(fake_gemini, reply):
    ai_replies(fake_gemini, reply)

    with pytest.raises(AIServiceError):
        parse_resume(RESUME_TEXT)


def test_gemini_failure_raises_ai_service_error(fake_gemini):
    fake_gemini.side_effect = RuntimeError("network down")

    with pytest.raises(AIServiceError, match="unavailable"):
        parse_resume(RESUME_TEXT)
