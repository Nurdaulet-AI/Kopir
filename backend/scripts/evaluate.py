"""Сравнение Kópir с типичными решениями на анкетах жюри.

    uv run python scripts/evaluate.py --label before

Результаты печатаются таблицей и сохраняются в eval/results/<label>.json,
чтобы «до» и «после» можно было сравнить честно.
"""

import argparse
import json
from pathlib import Path

from kopir.data.generator import DEFAULT_SIZE, generate
from kopir.evaluation.baselines import RECOMMENDERS
from kopir.evaluation.metrics import as_dict, data_ceiling, evaluate, hall_fairness, load_profiles

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "eval" / "queries.json"
RESULTS = ROOT / "eval" / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="имя прогона, например before/after")
    parser.add_argument("--n", type=int, default=DEFAULT_SIZE, help="размер синтетического зала")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    pool = generate(n=args.n, seed=args.seed)
    queries = load_profiles(QUERIES)

    quality = {name: evaluate(factory(pool), queries) for name, factory in RECOMMENDERS.items()}
    ceiling, starved = data_ceiling(pool, queries)
    hall = {"без анти-очереди": hall_fairness(pool, anti_queue=False),
            "с анти-очередью": hall_fairness(pool, anti_queue=True)}

    print(f"\n## Качество на {len(queries)} анкетах жюри, зал {len(pool)} человек (seed {args.seed})\n")
    print("| Решение | ≥3 из 5 подходят | Точность@5 | Нарушения взаимности | p95, мс |")
    print("|---|---|---|---|---|")
    for name, r in quality.items():
        print(f"| {name} | {r.jury_pass_rate:.0%} | {r.precision_at_5:.0%} | "
              f"{r.reciprocity_violations:.0%} | {r.p95_ms:.1f} |")
    print(f"| _Потолок данных_ | _{ceiling:.0%}_ | | | |")
    kopir_failed = quality["Kópir"].failed
    ranking_misses = [q for q in kopir_failed if q not in starved]
    print(f"\nНе прошли (Kópir): {len(kopir_failed)}. Из них в зале меньше 3 подходящих: "
          f"{', '.join(q for q in kopir_failed if q in starved) or 'нет'}; "
          f"ошибки ранжирования: {', '.join(ranking_misses) or 'нет'}")

    print("\n## Внимание зала (Kópir)\n")
    print("| Режим | Охват участников | Показов у самого популярного |")
    print("|---|---|---|")
    for name, h in hall.items():
        print(f"| {name} | {h.coverage:.0%} | {h.max_impressions} |")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{args.label}.json"
    payload = {"n": args.n, "seed": args.seed,
               "data_ceiling": ceiling, "starved_queries": starved,
               "quality": {k: as_dict(v) for k, v in quality.items()},
               "hall": {k: as_dict(v) for k, v in hall.items()}}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
