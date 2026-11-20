import itertools

import pytest

from kopir.data.generator import generate
from kopir.models import Profile, Target
from kopir.taxonomy import Goal, Level

_ids = itertools.count(1)


def make(goal: Goal, role: str = "backend", level: Level = Level.MIDDLE, years: float = 3, **kw) -> Profile:
    """Анкета с разумными значениями по умолчанию; тест задаёт только то, что проверяет."""
    target = kw.pop("target", None)
    return Profile(
        id=kw.pop("id", f"t{next(_ids)}"),
        name=kw.pop("name", "Тест"),
        role=role,
        level=level,
        years=years,
        goal=goal,
        target=target if isinstance(target, Target) else Target(**(target or {})),
        **kw,
    )


@pytest.fixture(scope="session")
def dataset() -> list[Profile]:
    return generate(n=200, seed=42)
