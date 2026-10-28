SYSTEM_PROMPT = """
You write short LinkedIn messages from a job candidate to a recruiter.

Rules:
- Write in the first person, as the candidate.
- Pick the 1-2 projects or skills from the resume that best match the job post, and mention 
them specifically.
- Only use facts from the resume. Never invent experience, skills or numbers.
- Use the recruiter's real name and the company name. Never write placeholders like [Name].
- Stay under the character limit you are given.
- Reply with the message only: no subject line, no quotes, no explanation.
"""

MESSAGE_TEMPLATE = """Write a {message_type} to {recruiter_name}, a recruiter at {company}.
Tone: {tone}.
Maximum length: {max_chars} characters.

<resume>
{resume_text}
</resume>

<job_post>
{job_text}
</job_post>"""

LENGTH_LIMITS = {
    "connection_note": 300,
    "inmail": 1000,
    "follow_up": 500,
}


def build_prompt(resume_text, job_text, company, recruiter_name, message_type, tone):
    return MESSAGE_TEMPLATE.format(
        message_type=message_type.replace("_", " "),
        recruiter_name=recruiter_name,
        company=company,
        tone=tone,
        max_chars=LENGTH_LIMITS[message_type],
        resume_text=resume_text,
        job_text=job_text,
    )
