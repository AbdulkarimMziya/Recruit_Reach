"""RecruitReach CLI: send your resume and a job post to the API, print the message.

Examples:
    # paste the job post when asked, then press Ctrl-D
    python cli/recruitreach.py --resume cv.docx \
        --company Shopify --recruiter "Sarah Lee" --type connection_note

    # or pipe it from the clipboard (Mac) / read it from a file
    pbpaste | python cli/recruitreach.py --job - --resume cv.docx ...
    python cli/recruitreach.py --job job.txt --resume cv.docx ...
"""

import argparse
import sys

import requests

MESSAGE_TYPES = ["connection_note", "inmail", "follow_up"]
TONES = ["friendly", "formal", "brief"]
TIMEOUT_SECONDS = 60  # the server may make two AI calls of up to 20 s each


def parse_args():
    """Read the command-line options (argparse tutorial)."""
    parser = argparse.ArgumentParser(description="Generate a LinkedIn message to a recruiter.")
    parser.add_argument("--resume", required=True, help="Path to your resume (.txt or .docx)")
    parser.add_argument(
        "--job",
        help="Path to a text file with the job post, or - to read it from a pipe. "
        "Leave it out to paste the job post when asked.",
    )
    parser.add_argument("--company", required=True, help="Company you're applying to")
    parser.add_argument(
        "--recruiter", required=True, help="Recruiter's name, as it should appear in the message"
    )
    parser.add_argument(
        "--type", required=True, choices=MESSAGE_TYPES, help="Kind of message to write"
    )
    parser.add_argument(
        "--tone", default="friendly", choices=TONES, help="Tone of the message (default: friendly)"
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Where the API runs (default: %(default)s)",
    )
    return parser.parse_args()


def read_job_text(source):
    """Get the job post text (Lesson 5).

    source is None -> ask the user to paste it (or read a pipe, if one is connected)
    source is "-"  -> read it from a pipe, e.g. `pbpaste | python cli/recruitreach.py --job -`
    anything else  -> treat it as a path to a text file
    """
    if source is None or source == "-":
        if source is None and sys.stdin.isatty():  # a person at the keyboard, not a pipe
            print(
                "Paste the job post, then press Ctrl-D on a new line "
                "(Windows: Ctrl-Z, then Enter):",
                file=sys.stderr,
            )
        text = sys.stdin.read()  # reads every line until Ctrl-D, unlike input()
    else:
        with open(source, encoding="utf-8") as job_file:
            text = job_file.read()

    if not text.strip():
        fail("the job post is empty.")
    return text


def send_request(args, job_text):
    """POST the resume and fields to the API and return the response (Lessons 3-4).

    The keys in `data` are the API's field names, which differ from some CLI option names.
    """
    data = {
        "company": args.company,
        "recruiter_name": args.recruiter,
        "job_text": job_text,
        "message_type": args.type,
        "tone": args.tone,
    }
    url = f"{args.api_url.rstrip('/')}/api/generate/"
    with open(args.resume, "rb") as resume_file:  # "rb": files are sent as bytes
        return requests.post(url, files={"resume": resume_file}, data=data, timeout=TIMEOUT_SECONDS)


def format_error(body):
    """Turn either error shape from the API into one readable line (Lesson 6).

    {"error": "..."}             -> from the view (400 / 503)
    {"field": ["message", ...]}  -> from the serializer (400)
    """
    if "error" in body:
        return body["error"]
    parts = []
    for field, messages in body.items():
        if isinstance(messages, list):
            messages = " ".join(str(m) for m in messages)
        parts.append(f"{field}: {messages}")
    return "; ".join(parts)


def fail(message):
    """Print an error to stderr and exit with code 1 (Lesson 7)."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    args = parse_args()

    try:
        job_text = read_job_text(args.job)
        response = send_request(args, job_text)
    except FileNotFoundError as e:
        fail(f"file not found: {e.filename}")
    except requests.ConnectionError:
        fail(f"can't reach the API at {args.api_url}. Is the server running?")
    except requests.Timeout:
        fail(f"the API took longer than {TIMEOUT_SECONDS} seconds to respond.")

    try:
        body = response.json()
    except ValueError:  # not JSON, e.g. an HTML error page
        fail(f"unexpected response from the API (HTTP {response.status_code}).")

    if response.status_code != 200:
        fail(format_error(body))

    print(body["message"])
    print(f"\n({body['char_count']} characters, {body['message_type']})")
    sys.exit(0)


if __name__ == "__main__":
    main()
