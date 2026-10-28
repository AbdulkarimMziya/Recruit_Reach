from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.conf import settings

from generator.errors import AIServiceError
from generator.services.generator import _call_ai, generate_message
from generator.services.prompts import LENGTH_LIMITS, SYSTEM_PROMPT, build_prompt

ARGS = dict(
    resume_text="Python, Django, built a task API",
    job_text="Junior backend developer, Python",
    company="Shopify",
    recruiter_name="Sarah",
    message_type="connection_note",
    tone="friendly",
)
LIMIT = LENGTH_LIMITS["connection_note"]


# ---------- build_prompt ----------


@pytest.mark.parametrize("message_type", list(LENGTH_LIMITS))
def test_build_prompt_fills_every_placeholder(message_type):
    prompt = build_prompt(**{**ARGS, "message_type": message_type})

    assert "{" not in prompt and "}" not in prompt
    assert f"{LENGTH_LIMITS[message_type]} characters" in prompt


def test_build_prompt_includes_resume_job_and_names():
    prompt = build_prompt(**ARGS)

    for value in (
        "Python, Django, built a task API",
        "Junior backend developer",
        "Shopify",
        "Sarah",
    ):
        assert value in prompt


# ---------- generate_message (our rules; _call_ai faked) ----------


def test_short_reply_is_returned_after_one_call():
    with patch("generator.services.generator._call_ai", return_value="Hi Sarah!") as mock:
        assert generate_message(**ARGS) == "Hi Sarah!"

    assert mock.call_count == 1
    system_prompt, user_prompt = mock.call_args.args
    assert system_prompt == SYSTEM_PROMPT
    assert "Sarah" in user_prompt


def test_too_long_reply_is_retried_once():
    replies = ["x" * (LIMIT + 1), "Hi Sarah, short."]
    with patch("generator.services.generator._call_ai", side_effect=replies) as mock:
        assert generate_message(**ARGS) == "Hi Sarah, short."

    assert mock.call_count == 2
    assert "too long" in mock.call_args.args[1]


def test_too_long_twice_raises():
    replies = ["x" * (LIMIT + 1), "y" * (LIMIT + 1)]
    with patch("generator.services.generator._call_ai", side_effect=replies):
        with pytest.raises(AIServiceError):
            generate_message(**ARGS)


def test_message_exactly_at_the_limit_is_accepted():
    with patch("generator.services.generator._call_ai", return_value="x" * LIMIT) as mock:
        assert len(generate_message(**ARGS)) == LIMIT

    assert mock.call_count == 1


def test_inmail_uses_its_own_longer_limit():
    long_reply = "x" * (LIMIT + 50)
    assert len(long_reply) <= LENGTH_LIMITS["inmail"]
    with patch("generator.services.generator._call_ai", return_value=long_reply) as mock:
        assert generate_message(**{**ARGS, "message_type": "inmail"}) == long_reply

    assert mock.call_count == 1


# ---------- _call_ai (the SDK faked by the fake_gemini fixture) ----------


def test_call_ai_sends_model_and_both_prompts(fake_gemini):
    _call_ai("the rules", "the request")

    kwargs = fake_gemini.call_args.kwargs
    assert kwargs["model"] == settings.AI_MODEL
    assert kwargs["contents"] == "the request"
    assert kwargs["config"].system_instruction == "the rules"


def test_call_ai_strips_the_reply(fake_gemini):
    fake_gemini.return_value = SimpleNamespace(text="  Hi Sarah!\n")

    assert _call_ai("rules", "request") == "Hi Sarah!"


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_call_ai_empty_reply_raises(fake_gemini, empty):
    fake_gemini.return_value = SimpleNamespace(text=empty)

    with pytest.raises(AIServiceError):
        _call_ai("rules", "request")


def test_call_ai_wraps_sdk_errors(fake_gemini):
    fake_gemini.side_effect = RuntimeError("network down")

    with pytest.raises(AIServiceError) as info:
        _call_ai("rules", "request")

    assert isinstance(info.value.__cause__, RuntimeError)
