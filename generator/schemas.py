"""The shape of a sorted resume.

Gemini sorts the raw resume text into this shape; Pydantic checks it.
Every section is required (it may be an empty list), so a section the AI
leaves out fails validation instead of silently disappearing.
"""

from pydantic import BaseModel


class Experience(BaseModel):
    id: str = ""                # filled by ResumeData.assign_ids, not the AI
    title: str                  # "Backend Developer Co-op"
    organisation: str
    date: str | None = None     # kept as text: "May 2025 - Aug 2025", "Present"
    bullets: list[str]


class Project(BaseModel):
    id: str = ""
    title: str  # the project name
    tech: list[str] = []
    date: str | None = None
    bullets: list[str]


class School(BaseModel):
    school: str
    credential: str               # "BSc Computer Science"
    date: str | None = None


class ResumeData(BaseModel):
    name: str
    experience: list[Experience]  # required, may be []
    projects: list[Project]
    education: list[School]
    skills: list[str]
    certifications: list[str]

    def assign_ids(self) -> "ResumeData":
        """Number every job and project: exp-1, exp-2, proj-1, ...

        A single bullet is its entry id plus its position, e.g. exp-1, index 1.
        """
        for i, job in enumerate(self.experience, start=1):
            job.id = f"exp-{i}"
        for i, project in enumerate(self.projects, start=1):
            project.id = f"proj-{i}"
        return self
