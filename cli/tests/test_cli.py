import io
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from cli import recruitreach

POST = "cli.recruitreach.requests.post"


# ---------- helpers ----------


@pytest.fixture
def files(tmp_path):
    """A real resume file and job post file in a temporary folder."""
    resume = tmp_path / "cv.txt"
    resume.write_text("Python, Django, built a task API")
    job = tmp_path / "job.txt"
    job.write_text("Junior backend developer, Python")
    return resume, job


def fake_response(status_code, body):
    response = MagicMock(status_code=status_code)
    response.json.return_value = body
    return response


def run_cli(monkeypatch, *args):
    """Run the CLI with these arguments and return its exit code."""
    monkeypatch.setattr(sys, "argv", ["recruitreach.py", *args])
    with pytest.raises(SystemExit) as exit_info:
        recruitreach.main()
    return exit_info.value.code


def base_args(resume, job=None):
    args = ["--resume", str(resume), "--company", "Shopify", "--recruiter", "Sarah"]
    args += ["--type", "connection_note"]
    if job is not None:
        args += ["--job", str(job)]
    return args


SUCCESS = {"message": "Hi Sarah!", "message_type": "connection_note", "char_count": 9}


# ---------- success ----------


def test_success_prints_message_and_exits_0(monkeypatch, capsys, files):
    resume, job = files
    with patch(POST, return_value=fake_response(200, SUCCESS)):
        code = run_cli(monkeypatch, *base_args(resume, job))

    assert code == 0
    output = capsys.readouterr().out
    assert "Hi Sarah!" in output
    assert "9 characters" in output


def test_sends_the_api_field_names(monkeypatch, files):
    resume, job = files
    with patch(POST, return_value=fake_response(200, SUCCESS)) as mock_post:
        run_cli(monkeypatch, *base_args(resume, job), "--tone", "formal")

    url = mock_post.call_args.args[0]
    kwargs = mock_post.call_args.kwargs
    assert url == "http://127.0.0.1:8000/api/generate/"
    assert kwargs["data"] == {
        "company": "Shopify",
        "recruiter_name": "Sarah",
        "job_text": "Junior backend developer, Python",
        "message_type": "connection_note",
        "tone": "formal",
    }
    assert "resume" in kwargs["files"]
    assert kwargs["timeout"] == recruitreach.TIMEOUT_SECONDS


def test_api_url_trailing_slash_is_handled(monkeypatch, files):
    resume, job = files
    with patch(POST, return_value=fake_response(200, SUCCESS)) as mock_post:
        run_cli(monkeypatch, *base_args(resume, job), "--api-url", "https://example.com/")

    assert mock_post.call_args.args[0] == "https://example.com/api/generate/"


# ---------- job post input ----------


def test_job_post_read_from_a_pipe(monkeypatch, files):
    resume, _ = files
    monkeypatch.setattr(sys, "stdin", io.StringIO("Pasted job post\nline two\n"))
    with patch(POST, return_value=fake_response(200, SUCCESS)) as mock_post:
        code = run_cli(monkeypatch, *base_args(resume), "--job", "-")

    assert code == 0
    assert mock_post.call_args.kwargs["data"]["job_text"] == "Pasted job post\nline two\n"


def test_empty_job_post_is_rejected_before_calling_the_api(monkeypatch, capsys, files):
    resume, _ = files
    monkeypatch.setattr(sys, "stdin", io.StringIO("   \n"))
    with patch(POST) as mock_post:
        code = run_cli(monkeypatch, *base_args(resume))

    assert code == 1
    assert "job post is empty" in capsys.readouterr().err
    mock_post.assert_not_called()


# ---------- errors ----------


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (400, {"resume": ["Only .txt and .docx files are allowed."]}, "resume: Only .txt"),
        (400, {"error": "The resume has no text in it."}, "The resume has no text in it."),
        (503, {"error": "The AI service is unavailable."}, "The AI service is unavailable."),
    ],
)
def test_api_errors_print_one_line_and_exit_1(monkeypatch, capsys, files, status, body, expected):
    resume, job = files
    with patch(POST, return_value=fake_response(status, body)):
        code = run_cli(monkeypatch, *base_args(resume, job))

    assert code == 1
    assert expected in capsys.readouterr().err


def test_missing_resume_file(monkeypatch, capsys, files, tmp_path):
    _, job = files
    with patch(POST) as mock_post:
        code = run_cli(monkeypatch, *base_args(tmp_path / "nope.docx", job))

    assert code == 1
    assert "file not found" in capsys.readouterr().err
    mock_post.assert_not_called()


def test_missing_job_file(monkeypatch, capsys, files, tmp_path):
    resume, _ = files
    code = run_cli(monkeypatch, *base_args(resume, tmp_path / "nope.txt"))

    assert code == 1
    assert "file not found" in capsys.readouterr().err


def test_server_not_running(monkeypatch, capsys, files):
    resume, job = files
    with patch(POST, side_effect=requests.ConnectionError()):
        code = run_cli(monkeypatch, *base_args(resume, job))

    assert code == 1
    assert "can't reach the API" in capsys.readouterr().err


def test_server_too_slow(monkeypatch, capsys, files):
    resume, job = files
    with patch(POST, side_effect=requests.Timeout()):
        code = run_cli(monkeypatch, *base_args(resume, job))

    assert code == 1
    assert "took longer" in capsys.readouterr().err


def test_non_json_response(monkeypatch, capsys, files):
    resume, job = files
    response = MagicMock(status_code=500)
    response.json.side_effect = ValueError("not json")
    with patch(POST, return_value=response):
        code = run_cli(monkeypatch, *base_args(resume, job))

    assert code == 1
    assert "HTTP 500" in capsys.readouterr().err


def test_invalid_type_is_rejected_by_argparse(monkeypatch, files):
    resume, job = files
    args = base_args(resume, job)
    args[args.index("connection_note")] = "email"
    with patch(POST) as mock_post:
        code = run_cli(monkeypatch, *args)

    assert code == 2  # argparse's exit code for bad arguments
    mock_post.assert_not_called()


# ---------- format_error ----------


def test_format_error_with_error_key():
    assert recruitreach.format_error({"error": "Down."}) == "Down."


def test_format_error_with_field_errors():
    body = {"tone": ['"angry" is not a valid choice.'], "company": ["This field is required."]}

    assert recruitreach.format_error(body) == (
        'tone: "angry" is not a valid choice.; company: This field is required.'
    )
