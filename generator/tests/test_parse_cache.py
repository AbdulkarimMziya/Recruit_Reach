import json
from types import SimpleNamespace

import pytest
from django.core.cache import cache

from generator.errors import AIServiceError
from generator.services.parser import CACHE_TIMEOUT, _cache_key, parse_resume

RESUME_TEXT = "Sam Lee\nDev Co-op, Acme\n- Built an API\nRecruitReach\n- Django REST API"


def sorted_resume():
    return {
        "name": "Sam Lee",
        "experience": [{"title": "Dev Co-op", "organisation": "Acme", "bullets": ["Built an API"]}],
        "projects": [{"title": "RecruitReach", "bullets": ["Django REST API"]}],
        "education": [],
        "skills": ["Python"],
        "certifications": [],
    }


def ai_replies(fake_gemini, text):
    fake_gemini.return_value = SimpleNamespace(text=text)


# ---------- the key ----------


def test_same_text_gives_the_same_key():
    assert _cache_key(RESUME_TEXT) == _cache_key(RESUME_TEXT)


def test_one_character_changes_the_key():
    assert _cache_key(RESUME_TEXT) != _cache_key(RESUME_TEXT + ".")


def test_key_has_prefix_and_version_but_not_the_resume():
    key = _cache_key(RESUME_TEXT)

    assert key.startswith("parse:v1:")
    assert len(key.split(":")[-1]) == 64  # a SHA-256 fingerprint
    assert "Sam Lee" not in key  # personal details never appear in the key


# ---------- hit and miss ----------


def test_same_resume_twice_calls_gemini_once(fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    first = parse_resume(RESUME_TEXT)
    second = parse_resume(RESUME_TEXT)

    assert fake_gemini.call_count == 1  # the second one was a hit
    assert second == first  # same data, ids included
    assert second.projects[0].id == "proj-1"


def test_different_resume_calls_gemini_again(fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    parse_resume(RESUME_TEXT)
    parse_resume(RESUME_TEXT + "\nSkills: Redis")

    assert fake_gemini.call_count == 2


def test_answer_is_saved_as_a_plain_dict(fake_gemini):
    """Redis stores data, not Python objects, so we save model_dump()."""
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    parse_resume(RESUME_TEXT)

    saved = cache.get(_cache_key(RESUME_TEXT))
    assert isinstance(saved, dict)
    assert saved["projects"][0]["id"] == "proj-1"  # ids are saved too


def test_saved_answer_is_used_without_calling_gemini(fake_gemini):
    saved = sorted_resume()
    saved["name"] = "From the cache"
    cache.set(_cache_key(RESUME_TEXT), saved, timeout=CACHE_TIMEOUT)

    data = parse_resume(RESUME_TEXT)

    assert data.name == "From the cache"
    fake_gemini.assert_not_called()


# ---------- failures are never cached ----------


def test_bad_answer_is_not_cached(fake_gemini):
    bad = sorted_resume()
    del bad["projects"]
    ai_replies(fake_gemini, json.dumps(bad))

    with pytest.raises(AIServiceError):
        parse_resume(RESUME_TEXT)

    assert cache.get(_cache_key(RESUME_TEXT)) is None  # nothing was saved

    ai_replies(fake_gemini, json.dumps(sorted_resume()))
    data = parse_resume(RESUME_TEXT)  # tries Gemini again, and works

    assert data.name == "Sam Lee"
    assert fake_gemini.call_count == 2


def test_gemini_down_is_not_cached(fake_gemini):
    fake_gemini.side_effect = RuntimeError("network down")

    with pytest.raises(AIServiceError):
        parse_resume(RESUME_TEXT)

    assert cache.get(_cache_key(RESUME_TEXT)) is None
