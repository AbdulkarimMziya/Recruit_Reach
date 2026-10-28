from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

from generator.errors import AIServiceError

URL = "/api/generate/"


def valid_form(**changes):
    form = {
        "resume": SimpleUploadedFile("cv.txt", b"Python, Django, built a task API"),
        "company": "Shopify",
        "recruiter_name": "Sarah",
        "job_text": "Junior backend developer, Python",
        "message_type": "inmail",
        "tone": "formal",
    }
    form.update(changes)
    return form


def test_view_passes_every_field_to_generate_message(client):
    with patch("generator.views.generate_message", return_value="Hi Sarah!") as mock:
        response = client.post(URL, valid_form(), format="multipart")

    assert response.status_code == 200
    mock.assert_called_once_with(
        resume_text="Python, Django, built a task API",
        company="Shopify",
        recruiter_name="Sarah",
        job_text="Junior backend developer, Python",
        message_type="inmail",
        tone="formal",
    )


def test_success_response_shape(client):
    with patch("generator.views.generate_message", return_value="Hi Sarah!"):
        response = client.post(URL, valid_form(), format="multipart")

    assert response.data == {"message": "Hi Sarah!", "message_type": "inmail", "char_count": 9}


def test_ai_failure_returns_503(client):
    with patch(
        "generator.views.generate_message",
        side_effect=AIServiceError("The AI service is unavailable. Please try again shortly."),
    ):
        response = client.post(URL, valid_form(), format="multipart")

    assert response.status_code == 503
    assert response.data == {"error": "The AI service is unavailable. Please try again shortly."}


def test_sdk_failure_end_to_end_returns_503(client, fake_gemini):
    fake_gemini.side_effect = RuntimeError("network down")

    response = client.post(URL, valid_form(), format="multipart")

    assert response.status_code == 503


def test_bad_upload_never_calls_the_ai(client, fake_gemini):
    form = valid_form(resume=SimpleUploadedFile("cv.pdf", b"x"))

    response = client.post(URL, form, format="multipart")

    assert response.status_code == 400
    fake_gemini.assert_not_called()


def test_blank_resume_never_calls_the_ai(client, fake_gemini):
    form = valid_form(resume=SimpleUploadedFile("cv.txt", b"   "))

    response = client.post(URL, form, format="multipart")

    assert response.status_code == 400
    fake_gemini.assert_not_called()
