---
name: recruiter-message
description: Write a LinkedIn message to a recruiter with RecruitReach. Use when the user asks for a connection note, InMail or follow-up to a recruiter, e.g. "/recruiter-message Franklin at Intuit".
---

# Recruiter message (RecruitReach)

Generate a LinkedIn message to a recruiter by running this repo's CLI, which calls the local RecruitReach API.

## 1. Check the server

Run `curl -s http://127.0.0.1:8000/api/health/`.
- `{"status":"ok"}` → continue.
- No answer → tell the user: "The RecruitReach server isn't running. Start it with `python manage.py runserver` in another terminal, then tell me." Wait for them.

## 2. Intake

Follow the **Intake** section of `AGENTS.md`: collect the job post, company, recruiter's name, resume path, message type and tone. Use anything given in the request (e.g. "Franklin at Intuit"), and ask for the rest one short question at a time. Never invent a recruiter's name or a resume path.

## 3. Run it

Pipe the job post in with `--job -` (you can't press Ctrl-D):

```bash
printf '%s' "<job post>" | python cli/recruitreach.py --job - \
  --resume "<resume path>" --company "<company>" --recruiter "<recruiter>" \
  --type <connection_note|inmail|follow_up> --tone <friendly|formal|brief>
```

Quote every value. If the job post contains `'` or `"`, write it to a temporary file instead and pass `--job <file>`.

## 4. Report

- **Exit code 0:** show the message exactly as printed, then its character count. Offer one follow-up (another type or tone).
- **Exit code 1:** show the `Error:` line and the likely fix:
  - `file not found` → ask for the correct resume path
  - `can't reach the API` → the server stopped; ask them to restart it
  - `AI_API_KEY or AI_MODEL is not set` → they need to fill in `.env` (don't open or print `.env` yourself)
  - an AI or quota error (503) → wait a minute, then offer to retry once
- **Exit code 2:** an invalid option; fix the command and run it again.

## Rules

- Don't edit the generated message; run the CLI again with different options instead.
- Don't read, print or commit `.env`.
- Don't call the Gemini API directly.
