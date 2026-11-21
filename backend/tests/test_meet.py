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
        intros = Introductions(sim_delay=0)
        beacons = {intros.request("x", f"p{i}", auto_accept=True).beacon for i in range(30)}
        assert len({(b.color, b.code) for b in beacons}) == 30

    def test_demo_participant_answers_after_delay_not_instantly(self):
        intros = Introductions(sim_delay=4)
        intro = intros.request("me", "p1", auto_accept=True, now=100.0)
        assert intro.status == "pending" and intro.beacon is None  # контактов ещё нет
        assert intros.of("me", now=103.0)[0].status == "pending"
        assert intros.of("me", now=104.5)[0].status == "accepted"

    def test_meeting_slots_never_double_book_a_person(self):
        intros = Introductions(sim_delay=0)
        times = [intros.request("me", f"p{i}", auto_accept=True).beacon.time for i in range(4)]
        assert times == ["18:00", "18:15", "18:30", "18:45"]
        other = intros.request("q", "p0", auto_accept=True).beacon.time  # p0 занят в 18:00
        assert other == "18:15"

    def test_group_shares_one_beacon_zone_and_time(self):
        intros = Introductions(sim_delay=0)
        group = [intros.request("me", f"p{i}", auto_accept=True, group="g1") for i in range(3)]
        assert len({(i.beacon.code, i.beacon.zone, i.beacon.time) for i in group}) == 1


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
        client.app.state.hall.introductions.sim_delay = 0
        view = client.post("/api/intros", json={"from_id": me, "to_id": "p050"}).json()
        assert view["status"] == "accepted" and view["simulated"] and view["beacon"]["code"]
        assert view["beacon"]["time"] == "18:00" and view["contact"]["looks_like"]
        assert view["contact"]["telegram"] is None  # вымышленный ник не ведёт к реальному аккаунту

    def test_contact_hidden_until_demo_participant_answers(self, client):
        me = self._join(client)
        view = client.post("/api/intros", json={"from_id": me, "to_id": "p051"}).json()
        assert view["status"] == "pending" and view["contact"] is None and view["beacon"] is None

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


# --- мини-группы ---

from kopir.matching.engine import Matcher  # noqa: E402
from kopir.squads import squad  # noqa: E402

# Абсолютная гарантия продукта, а не константа модуля: в группе нет бесполезных пар.
GROUP_FLOOR = 0.3


def _hall_profiles():
    return generate(n=300, seed=42)


def test_team_every_pair_is_mutually_useful_and_cofounder_roles_differ():
    profiles = _hall_profiles()
    matcher = Matcher(profiles)
    founders = [p for p in profiles if p.goal is Goal.FIND_COFOUNDER][:10]
    built = 0
    for me in founders:
        s = squad(me, matcher)
        if s is None:
            continue
        built += 1
        assert s.kind == "team" and 2 <= len(s.members) <= 3
        group = [me, *s.members]
        assert len({p.role for p in group}) == len(group)  # роли не повторяются
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                assert matcher.pair(a, b) >= GROUP_FLOOR - 1e-9
    assert built >= 5


def test_circle_has_one_mentor_and_mentees_of_that_mentor():
    profiles = _hall_profiles()
    matcher = Matcher(profiles)
    me = next(p for p in profiles if p.goal is Goal.FIND_MENTOR)
    s = squad(me, matcher)
    assert s is not None and s.kind == "circle"
    mentor, *others = s.members
    assert mentor.goal is Goal.BE_MENTOR
    assert all(o.goal is Goal.FIND_MENTOR and o.id != me.id for o in others)
    assert all(matcher.pair(mentor, o) >= GROUP_FLOOR for o in [*others, me])


def test_no_squads_for_jobs_market():
    profiles = _hall_profiles()
    matcher = Matcher(profiles)
    for goal in (Goal.FIND_JOB, Goal.HIRE):
        assert squad(next(p for p in profiles if p.goal is goal), matcher) is None


def test_squad_api():
    client = TestClient(create_app(Hall(generate(n=120, seed=4))))
    me = make(goal=Goal.SHARE_EXPERIENCE, role="backend", stack=["Python", "SQL"])
    r = client.post("/api/squad", json={"profile": me.model_dump(mode="json"), "lang": "kk"})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "team" and len(body["members"]) >= 2
    job = make(goal=Goal.FIND_JOB)
    assert client.post("/api/squad", json={"profile": job.model_dump(mode="json")}).json() is None


def test_squad_api_with_default_hall(monkeypatch, tmp_path):
    """Как на сервере: зал из файла по $KOPIR_PROFILES, а не переданный в create_app."""
    import json

    path = tmp_path / "profiles.json"
    path.write_text(json.dumps([p.model_dump(mode="json") for p in generate(n=120, seed=4)]), encoding="utf-8")
    monkeypatch.setenv("KOPIR_PROFILES", str(path))
    client = TestClient(create_app())
    me = make(goal=Goal.SHARE_EXPERIENCE, role="backend", stack=["Python", "SQL"])
    r = client.post("/api/squad", json={"profile": me.model_dump(mode="json")})
    assert r.status_code == 200 and r.json()["kind"] == "team"
