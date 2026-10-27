import os

from docx import Document

from ..errors import UnreadableResumeError


def extract_text(file) -> str:
    """Return the resume's plain text, or raise UnreadableResumeError."""
    ext = os.path.splitext(file.name)[1].lower()

    # 1. Read the file ONCE, in the way that matches its type.
    try:
        if ext == ".txt":
            text = file.read().decode("utf-8")  # bytes -> str
        elif ext == ".docx":
            doc = Document(file)  # python-docx opens the file object
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise UnreadableResumeError(f"Unsupported file type: {ext}")
    except UnreadableResumeError:
        raise  # our own error: pass it on unchanged
    except Exception as e:  # corrupt .docx, wrong text encoding...
        raise UnreadableResumeError("Could not read the file.") from e

    # 2. Only now can we know whether there's any real text.
    if not text.strip():
        raise UnreadableResumeError("The resume has no text in it.")

    return text
