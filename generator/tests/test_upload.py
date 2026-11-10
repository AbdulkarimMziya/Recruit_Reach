import io
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document
from pypdf import PdfWriter

from .conftest import FAKE_AI_MESSAGE

URL = "/api/generate/"
FIXTURES = Path(__file__).parent / "fixtures"


# ---------- helpers ----------


def make_docx(*paragraphs):
    """Build a real .docx in memory and return its bytes."""
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def make_blank_pdf():
    """A real PDF with one empty page (no text), built in memory."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # US letter size
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_form(resume, /, **changes):
    """A valid request, with optional changes. Pass a field as None to leave it out."""
    form = {
        "resume": resume,
        "company": "Acme",
        "recruiter_name": "Sam Lee",
        "job_text": "Backend developer, Python and Django",
        "message_type": "connection_note",
        "tone": "friendly",
    }
    form.update(changes)
    return {key: value for key, value in form.items() if value is not None}


def post(client, form):
    return client.post(URL, form, format="multipart")


# ---------- happy paths ----------


def test_txt_resume_returns_generated_message(client):
    content = b"Python, Django, REST APIs"
    resume = SimpleUploadedFile("cv.txt", content, content_type="text/plain")

    response = post(client, make_form(resume))

    assert response.status_code == 200
    assert response.data == {
        "message": FAKE_AI_MESSAGE,
        "message_type": "connection_note",
        "char_count": len(FAKE_AI_MESSAGE),
    }


def test_docx_resume_text_reaches_the_ai(client, fake_gemini):
    resume = SimpleUploadedFile("cv.docx", make_docx("Built a Django REST API", "Python"))

    response = post(client, make_form(resume))

    assert response.status_code == 200
    sent_prompt = fake_gemini.call_args.kwargs["contents"]
    assert "Built a Django REST API\nPython" in sent_prompt


def test_pdf_resume_text_reaches_the_ai(client, fake_gemini):
    content = (FIXTURES / "sample_resume.pdf").read_bytes()
    resume = SimpleUploadedFile("cv.pdf", content, content_type="application/pdf")

    response = post(client, make_form(resume))

    assert response.status_code == 200
    sent_prompt = fake_gemini.call_args.kwargs["contents"]
    assert "Built a Django REST API" in sent_prompt


def test_uppercase_extension_is_accepted(client):
    resume = SimpleUploadedFile("CV.TXT", b"Python")

    response = post(client, make_form(resume))

    assert response.status_code == 200


# ---------- the resume file ----------


@pytest.mark.parametrize("filename", ["cv.doc", "cv.exe", "cv"])
def test_wrong_file_type_returns_400(client, filename):
    resume = SimpleUploadedFile(filename, b"some content")

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert "resume" in response.data


def test_file_over_2mb_returns_400(client):
    resume = SimpleUploadedFile("cv.txt", b"a" * (2 * 1024 * 1024 + 1))

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert "resume" in response.data


def test_zero_byte_file_returns_400(client):
    resume = SimpleUploadedFile("cv.txt", b"")

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert "resume" in response.data


def test_whitespace_only_txt_returns_400(client):
    resume = SimpleUploadedFile("cv.txt", b"   \n\n  ")

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert response.data == {"error": "The resume has no text in it."}


def test_blank_docx_returns_400(client):
    resume = SimpleUploadedFile("cv.docx", make_docx())

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert response.data == {"error": "The resume has no text in it."}


def test_corrupt_docx_returns_400(client):
    resume = SimpleUploadedFile("cv.docx", b"this is not really a word file")

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert response.data == {"error": "Could not read the file."}


def test_blank_pdf_returns_400(client):
    resume = SimpleUploadedFile("cv.pdf", make_blank_pdf())

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert response.data == {"error": "The resume has no text in it."}


def test_corrupt_pdf_returns_400(client):
    resume = SimpleUploadedFile("cv.pdf", b"this is not really a pdf")

    response = post(client, make_form(resume))

    assert response.status_code == 400
    assert response.data == {"error": "Could not read the file."}


# ---------- the other fields ----------


def test_invalid_tone_returns_400(client):
    resume = SimpleUploadedFile("cv.txt", b"Python")

    response = post(client, make_form(resume, tone="angry"))

    assert response.status_code == 400
    assert "tone" in response.data


def test_invalid_message_type_returns_400(client):
    resume = SimpleUploadedFile("cv.txt", b"Python")

    response = post(client, make_form(resume, message_type="email"))

    assert response.status_code == 400
    assert "message_type" in response.data


@pytest.mark.parametrize(
    "missing", ["resume", "company", "recruiter_name", "job_text", "message_type"]
)
def test_missing_required_field_returns_400(client, missing):
    resume = SimpleUploadedFile("cv.txt", b"Python")

    response = post(client, make_form(resume, **{missing: None}))

    assert response.status_code == 400
    assert missing in response.data
