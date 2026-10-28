from types import SimpleNamespace
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

FAKE_AI_MESSAGE = "Hi Sam, I built a Django REST API and would love to connect."


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture(autouse=True)
def fake_gemini():
    """Replace the Gemini SDK call in EVERY test, so no test ever calls the real API.

    Tests can change what it returns (`fake_gemini.return_value = ...`) or make it
    fail (`fake_gemini.side_effect = SomeError(...)`), and check what was sent
    (`fake_gemini.call_args.kwargs["contents"]`).
    """
    with patch("google.genai.models.Models.generate_content") as mock:
        mock.return_value = SimpleNamespace(text=FAKE_AI_MESSAGE)
        yield mock
