class RecruitReachError(Exception):
    """Base class for every error this app raises on purpose."""


class UnreadableResumeError(RecruitReachError):
    """The resume couldn't be read or had no text. The view returns 400."""


class AIServiceError(RecruitReachError):
    """The AI call failed, timed out, or never fit the length limit. The view returns 503."""
