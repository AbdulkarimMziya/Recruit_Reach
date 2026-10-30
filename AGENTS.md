# AGENTS.md

Instructions for AI coding agents (Claude Code, Cursor, Codex, ...) working in this repo or using RecruitReach.

## What this project is

A Django REST API plus a CLI. You give it a resume (`.txt` or `.docx`) and a job post; it returns a short LinkedIn message to the recruiter that highlights the candidate's most relevant projects. It runs locally; the AI call uses the person's own Gemini API key from `.env`.

## Intake: collect everything before running

Before running the CLI, make sure you have all six inputs. Ask the user for anything missing, **one short question at a time**, in this order. Never guess or invent a value.

| # | Input | If missing |
| --- | --- | --- |
| 1 | **Job post** | ask: "Paste the job description." Use the full text they paste, unchanged. |
| 2 | **Company** | ask, unless it's clearly named in the job post; if you take it from the post, say so |
| 3 | **Recruiter's name** | always ask; never take a name from the job post or make one up |
| 4 | **Resume path** | **always ask, for every message**: the user keeps a custom resume per application. Ask for the path to a `.txt` or `.docx` file. You may offer the last one used as an option, but only use it if they confirm. |
| 5 | **Message type** | ask: connection note (≤300 chars), InMail (≤1000) or follow-up (≤500)? |
| 6 | **Tone** | ask: friendly, formal or brief? |

- If the user says "use the defaults", use `connection_note` and `friendly` for 5 and 6. Never default 1–4, and never reuse a resume without asking.
- Several inputs given at once ("connection note to Franklin at Intuit, friendly") count; only ask for what's still missing.
- Before running, restate the inputs in one line (e.g. "Connection note to Franklin at Intuit, friendly, using `Resume.docx`.") and run it.
- After the result: show the message exactly as returned, with its character count. Offer one follow-up, e.g. "Want an InMail or a different tone?" Don't edit the message yourself: run the CLI again with different options instead.

## Generating a message (the main task)

1. Make sure the server is running (in its own terminal): `python manage.py runserver`
   - Check: `curl -s http://127.0.0.1:8000/api/health/` returns `{"status":"ok"}`
2. Run the CLI. Agents can't press Ctrl-D, so **pipe the job post in with `--job -`**:

```bash
printf '%s' "<job post text>" | python cli/recruitreach.py --job - \
  --resume "/path/to/resume.docx" \
  --company "Intuit" \
  --recruiter "Franklin" \
  --type connection_note \
  --tone friendly
```

| Option | Required | Values |
| --- | --- | --- |
| `--resume` | yes | path to a `.txt` or `.docx` file (quote paths with spaces) |
| `--job` | for agents: yes, use `-` | `-` = read from stdin; or a path to a text file |
| `--company` | yes | text |
| `--recruiter` | yes | the recruiter's name as it should appear |
| `--type` | yes | `connection_note` (≤300 chars), `inmail` (≤1000), `follow_up` (≤500) |
| `--tone` | no | `friendly` (default), `formal`, `brief` |
| `--api-url` | no | default `http://127.0.0.1:8000` |

- **Success:** the message on stdout, then `(<n> characters, <type>)`; exit code 0.
- **Failure:** one line starting with `Error:` on stderr; exit code 1 (2 for invalid options).
- Run `python cli/recruitreach.py --help` if unsure.

### Running several at once

Two or three requests in parallel are fine. More can hit the Gemini free tier's per-minute limit, which comes back as an `Error:` line (HTTP 503). If that happens, wait a minute and retry; don't loop rapidly.

### Don't

- Don't invent the recruiter's name or company; ask the user if they weren't given.
- Don't read, print or commit `.env` (it holds the user's API key).
- Don't call the Gemini API directly; always go through the CLI or `POST /api/generate/`.

## Working on the code

- Setup: `cp .env.example .env` (add a Gemini key), `pip install -r requirements.txt`, `python manage.py migrate`
- Before every commit: `ruff check .`, `ruff format --check .`, `pytest` (all must pass; CI runs the same)
- Tests never call Gemini or a real server: `generator/tests/conftest.py` fakes the Gemini SDK for every test, and the CLI tests fake `requests.post`. Keep it that way.

| Where | What |
| --- | --- |
| `generator/views.py` | HTTP only: validate, call services, map errors to 400 / 503 |
| `generator/serializers.py` | request validation and the response shape (used by the API docs) |
| `generator/services/resume.py` | reads text from `.txt` / `.docx` |
| `generator/services/prompts.py` | system prompt, message template, length limits |
| `generator/services/generator.py` | `_call_ai` (the only code that talks to Gemini) and `generate_message` |
| `generator/errors.py` | `RecruitReachError` → `UnreadableResumeError` (400), `AIServiceError` (503) |
| `cli/recruitreach.py` | the command-line client |

- Keep views thin; new logic goes in `services/`.
- Line length is 100 (Ruff).
