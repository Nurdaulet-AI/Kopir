import json

import pytest
from fastapi.testclient import TestClient

from kopir.api.app import create_app
from kopir.data.generator import generate
from kopir.hall import Hall
from kopir.taxonomy import Goal

SEEKER = {
    "id": "attacker-chosen-id",
    "name": "Жюри Тест",
    "lang": "kk",
    "role": "backend",
    "level": "junior",
    "years": 1.5,
    "stack": ["python", "FastAPI", "postgres"],
    "interests": ["fintech"],
    "goal": "find_job",
    "target": {"roles": ["backend"]},
    "about": "Junior Python-әзірлеуші, жұмыс іздеймін.",
}


@pytest.fixture
def client():
    return TestClient(create_app(Hall(generate(n=150, seed=5))))


def _recommend(client, **body):
    return client.post("/api/recommend", json={"profile": SEEKER, **body})


def test_health_reports_hall_size(client):
    assert client.get("/api/health").json() == {"status": "ok", "profiles": 150}


def test_options_are_localised(client):
    kk = client.get("/api/options", params={"lang": "kk"}).json()
    assert {o["value"] for o in kk["goals"]} == set(Goal)
    assert next(o["label"] for o in kk["goals"] if o["value"] == "find_cofounder") == "Тең құрылтайшы табу"
    assert "Python" in kk["skills"]


def test_recommend_returns_explained_reciprocal_top5(client):
    r = _recommend(client)
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "kk" and len(body["recommendations"]) == 5
    for rec in body["recommendations"]:
        assert rec["candidate"]["goal"] == "hire"
        assert 0 <= rec["score"] <= 100
        e = rec["explanation"]
        assert e["label_you"] == "Сізге" and e["for_me"] and e["for_them"] and e["icebreaker"]
    assert body["elapsed_ms"] < 3000


def test_explanation_language_can_differ_from_profile(client):
    body = _recommend(client, lang="en").json()
    assert body["recommendations"][0]["explanation"]["label_you"] == "For you"


def test_contacts_are_never_exposed(client):
    raw = json.dumps(_recommend(client).json(), ensure_ascii=False)
    assert "telegram" not in raw and "looks_like" not in raw and "@" not in raw


def test_server_assigns_the_profile_id(client):
    assert _recommend(client).json()["profile_id"] != SEEKER["id"]


def test_show_more_excludes_already_seen(client):
    first = [r["candidate"]["id"] for r in _recommend(client).json()["recommendations"]]
    more = [r["candidate"]["id"] for r in _recommend(client, exclude=first).json()["recommendations"]]
    assert more and not set(first) & set(more)


def test_joined_profile_is_recommended_to_others(client):
    me = _recommend(client, join=True).json()
    assert client.get("/api/health").json()["profiles"] == 151
    hirer = {"name": "HR", "role": "recruiter", "level": "senior", "years": 6, "goal": "hire",
             "openings": [{"roles": ["backend"], "skills": ["Python", "FastAPI"], "level": "junior"}]}
    recs = client.post("/api/recommend", json={"profile": hirer, "k": 20}).json()["recommendations"]
    assert me["profile_id"] in {r["candidate"]["id"] for r in recs}


@pytest.mark.parametrize(
    "broken",
    [
        {"goal": "hire", "target": {}},  # нанимающий без вакансии
        {"lang": "de"},
        {"level": "guru"},
        {"years": -1},
    ],
)
def test_invalid_profiles_are_rejected(client, broken):
    assert client.post("/api/recommend", json={"profile": {**SEEKER, **broken}}).status_code == 422


def test_k_is_bounded(client):
    assert _recommend(client, k=0).status_code == 422
    assert _recommend(client, k=100).status_code == 422


class TestWebUi:
    def test_serves_index_and_keeps_api_routes(self, tmp_path):
        (tmp_path / "index.html").write_text("<!doctype html><title>Kópir</title>", encoding="utf-8")
        client = TestClient(create_app(Hall(generate(n=60, seed=1)), web_dir=tmp_path))
        assert "Kópir" in client.get("/").text
        assert client.get("/api/health").json()["status"] == "ok"

    def test_missing_build_fails_loudly(self, tmp_path):
        with pytest.raises(RuntimeError, match="npm run build"):
            create_app(Hall(generate(n=60, seed=1)), web_dir=tmp_path)
