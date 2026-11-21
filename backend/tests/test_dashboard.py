import pytest
from fastapi.testclient import TestClient

from conftest import make
from kopir.api.app import create_app
from kopir.dashboard import build, hall_map
from kopir.data.generator import generate
from kopir.hall import Hall
from kopir.taxonomy import Goal


@pytest.fixture(scope="module")
def board(dataset):
    return build(dataset, "ru")


def test_counts_add_up(board, dataset):
    assert board.participants == len(dataset)
    assert sum(g["count"] for g in board.goals) == len(dataset)
    seekers = sum(p.goal == Goal.FIND_JOB for p in dataset)
    assert sum(r["seekers"] for r in board.roles) <= seekers
    assert board.openings == sum(len(p.openings) for p in dataset if p.goal == Goal.HIRE)
    assert 0 <= board.well_matched <= 1


def test_map_points_are_normalised_and_cover_everyone(board, dataset):
    assert len(board.points) == len(dataset)
    assert all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in board.points)
    assert {p["market"] for p in board.points} == {"jobs", "mentoring", "startups"}


def test_similar_profiles_land_close_on_the_map():
    twins = [make(Goal.FIND_JOB, stack=["Python", "FastAPI"], interests=["fintech"]) for _ in range(2)]
    other = make(Goal.BE_MENTOR, role="designer", stack=["Figma"], interests=["gaming"], years=9)
    coords = hall_map([*twins, other, make(Goal.HIRE, target={"roles": ["qa"], "skills": ["Selenium"]})])
    assert abs(coords[0] - coords[1]).sum() < abs(coords[0] - coords[2]).sum()


def test_insight_about_missing_openings():
    seekers = [make(Goal.FIND_JOB, role="qa", stack=["Selenium"]) for _ in range(5)]
    hirer = make(Goal.HIRE, target={"roles": ["backend"], "skills": ["Go"]})
    board = build([*seekers, hirer], "ru")
    assert any(i["kind"] == "few_openings" and "QA-инженер" in i["text"] for i in board.insights)


def test_insights_in_every_language(dataset):
    for lang in ("ru", "kk", "en"):
        insights = build(dataset, lang).insights
        assert insights and all(i["text"] and "{" not in i["text"] for i in insights)


def test_api_serves_dashboard():
    client = TestClient(create_app(Hall(generate(n=80, seed=2))))
    body = client.get("/api/dashboard", params={"lang": "kk"}).json()
    assert body["participants"] == 80 and body["points"] and body["insights"]
