import json
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

URL = "/api/resumes/parse/"


def sorted_resume():
    """A good answer from (fake) Gemini."""
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


def upload(client, resume):
    return client.post(URL, {"resume": resume}, format="multipart")


def txt_resume(content=b"Sam Lee\nDev Co-op, Acme\n- Built an API"):
    return SimpleUploadedFile("cv.txt", content, content_type="text/plain")


# ---------- happy path ----------


def test_returns_the_sorted_resume_with_ids(client, fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    response = upload(client, txt_resume())

    assert response.status_code == 200
    assert response.data["name"] == "Sam Lee"
    assert response.data["experience"][0]["id"] == "exp-1"
    assert response.data["projects"][0]["id"] == "proj-1"
    assert response.data["projects"][0]["bullets"] == ["Django REST API"]


def test_the_resume_text_reaches_the_ai(client, fake_gemini):
    ai_replies(fake_gemini, json.dumps(sorted_resume()))

    upload(client, txt_resume(b"Built a Django REST API"))

    assert "Built a Django REST API" in fake_gemini.call_args.kwargs["contents"]


# ---------- bad uploads (400) ----------


def test_missing_file_returns_400(client):
    response = client.post(URL, {}, format="multipart")

    assert response.status_code == 400
    assert "resume" in response.data


@pytest.mark.parametrize("filename", ["cv.doc", "cv.exe", "cv"])
def test_wrong_file_type_returns_400(client, filename):
    response = upload(client, SimpleUploadedFile(filename, b"some content"))

    assert response.status_code == 400
    assert "resume" in response.data


def test_empty_resume_returns_400_without_calling_the_ai(client, fake_gemini):
    response = upload(client, txt_resume(b"   \n  "))

    assert response.status_code == 400
    assert response.data == {"error": "The resume has no text in it."}
    fake_gemini.assert_not_called()


# ---------- AI problems (503) ----------


def test_wrong_shaped_ai_answer_returns_503(client, fake_gemini):
    answer = sorted_resume()
    del answer["projects"]
    ai_replies(fake_gemini, json.dumps(answer))

    response = upload(client, txt_resume())

    assert response.status_code == 503
    assert response.data == {"error": "The AI's answer didn't match the resume format."}


def test_ai_down_returns_503(client, fake_gemini):
    fake_gemini.side_effect = RuntimeError("network down")

    response = upload(client, txt_resume())

    assert response.status_code == 503
    assert "unavailable" in response.data["error"]
