import pytest
from pydantic import ValidationError

from conftest import make
from kopir.models import Target
from kopir.taxonomy import Goal


def test_short_hirer_form_moves_vacancy_into_openings():
    hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["golang"]})
    assert hirer.openings == [Target(roles=["backend"], skills=["Go"])]
    assert hirer.target == Target()


def test_hirer_without_vacancy_is_rejected():
    with pytest.raises(ValidationError, match="вакансия"):
        make(Goal.HIRE)


def test_every_opening_needs_a_role():
    with pytest.raises(ValidationError, match="вакансия"):
        make(Goal.HIRE, openings=[{"roles": ["backend"]}, {"skills": ["Python"]}])


def test_only_hirers_have_openings():
    with pytest.raises(ValidationError, match="только у нанимающих"):
        make(Goal.FIND_JOB, openings=[{"roles": ["backend"]}])


def test_unknown_values_are_dropped_not_kept():
    p = make(Goal.FIND_JOB, stack=["питон", "квантовая йога"], interests=["fintech", "astrology"])
    assert p.stack == ["Python"]
    assert p.interests == ["fintech"]
