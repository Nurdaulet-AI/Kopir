"""Сравнение Kópir с типичными решениями на анкетах жюри.

    uv run python scripts/evaluate.py --label v3                     # основной набор
    uv run python scripts/evaluate.py --label v3 --queries holdout   # контрольный набор

Каждый прогон строит несколько синтетических залов (seeds) и усредняет метрики:
один зал может оказаться удачным или неудачным случайно. Результаты печатаются
таблицей и сохраняются в eval/results/<label>-<queries>.json.

Контрольный набор (holdout) не использовался при настройке модели и генератора:
итоговые цифры для README берутся по нему.
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from kopir.data.generator import DEFAULT_SIZE, generate
from kopir.evaluation.baselines import RECOMMENDERS
from kopir.evaluation.metrics import as_dict, data_ceiling, evaluate, hall_fairness, load_profiles

ROOT = Path(__file__).resolve().parent.parent
QUERY_SETS = {"dev": ROOT / "eval" / "queries.json", "holdout": ROOT / "eval" / "holdout.json"}
RESULTS = ROOT / "eval" / "results"


def _mean_std(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def _fmt(values: list[float]) -> str:
    mean, std = _mean_std(values)
    return f"{mean:.0%} ± {std:.0%}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="имя прогона, например v3")
    parser.add_argument("--queries", choices=list(QUERY_SETS), default="dev")
    parser.add_argument("--n", type=int, default=DEFAULT_SIZE, help="размер синтетического зала")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    args = parser.parse_args()

    queries = load_profiles(QUERY_SETS[args.queries])
    quality: dict[str, dict[str, list[float]]] = {
        name: {"jury_pass_rate": [], "precision_at_5": [], "reciprocity_violations": [], "p95_ms": []}
        for name in RECOMMENDERS
    }
    ceilings: list[float] = []
    starved: Counter[str] = Counter()
    ranking_misses: Counter[str] = Counter()

    for seed in args.seeds:
        pool = generate(n=args.n, seed=seed)
        ceiling, starved_now = data_ceiling(pool, queries)
        ceilings.append(ceiling)
        starved.update(starved_now)
        for name, factory in RECOMMENDERS.items():
            report = evaluate(factory(pool), queries)
            for metric, values in quality[name].items():
                values.append(getattr(report, metric))
            if name == "Kópir":
                ranking_misses.update(q for q in report.failed if q not in starved_now)

    hall_pool = generate(n=args.n, seed=args.seeds[0])
    hall = {"без анти-очереди": hall_fairness(hall_pool, anti_queue=False),
            "с анти-очередью": hall_fairness(hall_pool, anti_queue=True)}

    print(f"\n## {args.queries}: {len(queries)} анкет, зал {args.n} человек, залов {len(args.seeds)}\n")
    print("| Решение | ≥3 из 5 подходят | Точность@5 | Нарушения взаимности | p95, мс |")
    print("|---|---|---|---|---|")
    for name, m in quality.items():
        print(f"| {name} | {_fmt(m['jury_pass_rate'])} | {_fmt(m['precision_at_5'])} | "
              f"{_fmt(m['reciprocity_violations'])} | {statistics.mean(m['p95_ms']):.1f} |")
    print(f"| _Потолок данных_ | _{_fmt(ceilings)}_ | | | |")
    print(f"\nОшибки ранжирования Kópir (анкета: в скольких залах): {dict(ranking_misses) or 'нет'}")
    print(f"Мало подходящих людей в зале (анкета: в скольких залах): {dict(starved) or 'нет'}")

    print(f"\n## Внимание зала (Kópir, seed {args.seeds[0]})\n")
    print("| Режим | Охват участников | Показов у самого популярного |")
    print("|---|---|---|")
    for name, h in hall.items():
        print(f"| {name} | {h.coverage:.0%} | {h.max_impressions} |")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{args.label}-{args.queries}.json"
    payload = {
        "queries": args.queries, "n": args.n, "seeds": args.seeds,
        "data_ceiling": _mean_std(ceilings),
        "quality": {name: {k: _mean_std(v) for k, v in m.items()} for name, m in quality.items()},
        "ranking_misses": dict(ranking_misses), "starved": dict(starved),
        "hall": {k: as_dict(v) for k, v in hall.items()},
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
