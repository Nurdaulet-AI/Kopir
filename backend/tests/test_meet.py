import pytest
from fastapi.testclient import TestClient

from conftest import make
from kopir.api.app import create_app
from kopir.data.generator import generate
from kopir.hall import Hall
from kopir.meet import Introductions, schedule
from kopir.taxonomy import Goal
from kopir.voice import parse


class TestDoubleOptIn:
    def test_contact_opens_only_after_both_agree(self):
        intros = Introductions()
        intro = intros.request("a", "b", auto_accept=False)
        assert intro.status == "pending" and intro.beacon is None
        accepted = intros.respond(intro.id, "b", accept=True)
        assert accepted.status == "accepted" and accepted.beacon is not None

    def test_only_recipient_can_answer(self):
        intros = Introductions()
        intro = intros.request("a", "b", auto_accept=False)
        with pytest.raises(KeyError):
            intros.respond(intro.id, "a", accept=True)

    def test_mutual_interest_is_consent(self):
        intros = Introductions()
        first = intros.request("a", "b", auto_accept=False)
        second = intros.request("b", "a", auto_accept=False)
        assert second.id == first.id and second.status == "accepted"

    def test_beacons_are_unique(self):
        intros = Introductions()
        beacons = {intros.request("x", f"p{i}", auto_accept=True).beacon for i in range(30)}
        assert len({(b.color, b.code) for b in beacons}) == 30


def test_schedule_has_no_double_booking_or_repeats(dataset):
    plan = schedule(dataset[:120], slots=4)
    seen_pairs = set()
    for slot in plan:
        people = [p.id for m in slot for p in (m.a, m.b)]
        assert len(people) == len(set(people))
        for m in slot:
            pair = frozenset((m.a.id, m.b.id))
            assert pair not in seen_pairs
            seen_pairs.add(pair)
    assert sum(len(s) for s in plan) > 0


@pytest.mark.parametrize(("text", "role", "goal"), [
    ("Я junior бэкенд на Python и FastAPI, 2 года, ищу работу в финтехе", "backend", Goal.FIND_JOB),
    ("Мен Flutter әзірлеушімін, жұмыс іздеймін", "mobile", Goal.FIND_JOB),
    ("Senior ML engineer, 7 years with PyTorch and LLM, happy to mentor others", "ml", Goal.BE_MENTOR),
])
def test_free_text_becomes_profile_fields(text, role, goal):
    p = parse(text)
    assert p.role == role and p.goal == goal
    assert p.stack


def test_parse_extracts_skills_years_and_domain():
    p = parse("Пишу на питоне и golang, 3 года опыта, интересен финтех")
    assert p.stack[:2] == ["Python", "Go"] and p.years == 3 and "fintech" in p.interests


class TestApi:
    @pytest.fixture
    def client(self):
        return TestClient(create_app(Hall(generate(n=80, seed=4))))

    def _join(self, client, **extra):
        profile = {"name": "Я", "role": "backend", "level": "junior", "years": 1, "stack": ["Python"],
                   "goal": "find_job", "target": {"roles": ["backend"]}, "telegram": "@me", **extra}
        return client.post("/api/profiles", json={"profile": profile}).json()["profile_id"]

    def test_demo_participant_accepts_and_reveals_contact(self, client):
        me = self._join(client)
        view = client.post("/api/intros", json={"from_id": me, "to_id": "p050"}).json()
        assert view["status"] == "accepted" and view["simulated"] and view["beacon"]["code"]
        assert view["contact"]["telegram"]

    def test_live_people_need_both_yes(self, client):
        a = self._join(client)
        b = self._join(client, name="Жюри", telegram="@jury")
        sent = client.post("/api/intros", json={"from_id": a, "to_id": b}).json()
        assert sent["status"] == "pending" and sent["contact"] is None
        inbox = client.get("/api/intros", params={"profile_id": b}).json()
        assert inbox[0]["direction"] == "incoming" and inbox[0]["contact"] is None
        answered = client.post(f"/api/intros/{sent['id']}/respond", json={"profile_id": b, "accept": True}).json()
        assert answered["contact"]["telegram"] == "@me"

    def test_unknown_sender_is_rejected(self, client):
        assert client.post("/api/intros", json={"from_id": "nobody", "to_id": "p001"}).status_code == 404

    def test_dashboard_has_schedule(self, client):
        body = client.get("/api/dashboard").json()
        assert len(body["slots"]) == 4 and body["slots"][0]["meetings"] and 0 < body["scheduled"] <= 1
