from pathlib import Path

import pytest

from kopir.data.generator import generate
from kopir.evaluation.baselines import RECOMMENDERS
from kopir.evaluation.metrics import data_ceiling, evaluate, hall_fairness, load_profiles

QUERIES = Path(__file__).resolve().parent.parent / "eval" / "queries.json"


@pytest.fixture(scope="module")
def small_hall():
    return generate(n=120, seed=3)


@pytest.mark.parametrize("name", list(RECOMMENDERS))
def test_no_recommender_beats_the_data_ceiling(small_hall, name):
    """Если метрика показывает результат выше потолка, сломана метрика, а не побит рекорд."""
    queries = load_profiles(QUERIES)
    ceiling, _ = data_ceiling(small_hall, queries)
    assert evaluate(RECOMMENDERS[name](small_hall), queries).jury_pass_rate <= ceiling


def test_anti_queue_spreads_attention(small_hall):
    plain = hall_fairness(small_hall, anti_queue=False)
    balanced = hall_fairness(small_hall, anti_queue=True)
    assert balanced.max_impressions < plain.max_impressions
    assert balanced.coverage >= plain.coverage
