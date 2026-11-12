import json

import pytest
from pydantic import ValidationError

from generator.schemas import ResumeData

SECTIONS = ["experience", "projects", "education", "skills", "certifications"]


def valid_resume():
    """A complete, valid resume. Each test copies it and changes one thing."""
    return {
        "name": "Sam Lee",
        "experience": [{"title": "Dev Co-op", "organisation": "Acme", "bullets": ["Built an API"]}],
        "projects": [{"title": "RecruitReach", "bullets": ["Django REST API"]}],
        "education": [],
        "skills": ["Python"],
        "certifications": [],
    }


# ---------- good data ----------


def test_valid_dict_parses():
    data = ResumeData.model_validate(valid_resume())

    assert data.name == "Sam Lee"
    assert data.experience[0].organisation == "Acme"
    assert data.projects[0].title == "RecruitReach"


def test_valid_json_text_parses():
    """Gemini sends back a JSON string, so this is the path its answer takes."""
    raw = json.dumps(valid_resume())

    data = ResumeData.model_validate_json(raw)

    assert data.projects[0].bullets == ["Django REST API"]


def test_empty_section_is_allowed():
    """Empty is fine ("no certifications"); missing is not (next test)."""
    resume = valid_resume()
    resume["certifications"] = []

    data = ResumeData.model_validate(resume)

    assert data.certifications == []


# ---------- bad data ----------


@pytest.mark.parametrize("section", SECTIONS)
def test_missing_section_fails(section):
    resume = valid_resume()
    del resume[section]

    with pytest.raises(ValidationError) as error:
        ResumeData.model_validate(resume)

    assert error.value.errors()[0]["loc"] == (section,)


def test_bullets_as_a_string_fails():
    """One string where a list belongs would later be looped letter by letter."""
    resume = valid_resume()
    resume["experience"][0]["bullets"] = "Built an API"

    with pytest.raises(ValidationError):
        ResumeData.model_validate(resume)


# ---------- ids ----------


def test_assign_ids_numbers_jobs_and_projects():
    resume = valid_resume()
    resume["experience"].append({"title": "Tutor", "organisation": "TRU", "bullets": []})
    resume["projects"].append({"title": "Hire Horizon", "bullets": []})

    data = ResumeData.model_validate(resume).assign_ids()

    assert [job.id for job in data.experience] == ["exp-1", "exp-2"]
    assert [project.id for project in data.projects] == ["proj-1", "proj-2"]


def test_ids_come_from_our_code_not_the_ai():
    """Even if the AI sends its own ids, assign_ids replaces them."""
    resume = valid_resume()
    resume["projects"][0]["id"] = "made-up-by-ai"

    data = ResumeData.model_validate(resume).assign_ids()

    assert data.projects[0].id == "proj-1"
