"""Выгружает синтетический зал в data/profiles.json и data/profiles.csv (файл анкет для сдачи).

    uv run python scripts/export_profiles.py

JSON — источник для сервера (полная структура, включая вакансии). CSV — для
просмотра в таблице: списки через «;», вакансии одной JSON-строкой.
"""

import argparse
import csv
import json
from pathlib import Path

from kopir.data.generator import DEFAULT_SIZE, generate
from kopir.hall import DEFAULT_SEED

DATA = Path(__file__).resolve().parents[2] / "data"

CSV_COLUMNS = (
    "id", "name", "telegram", "lang", "city", "role", "level", "years", "stack", "interests",
    "goal", "target_roles", "target_skills", "target_level", "target_domains", "openings",
    "company", "looks_like", "about",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    profiles = generate(n=args.n, seed=args.seed)
    DATA.mkdir(exist_ok=True)

    records = [p.model_dump(mode="json") for p in profiles]
    (DATA / "profiles.json").write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    with (DATA / "profiles.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in records:
            t = r["target"]
            writer.writerow({
                **{k: r[k] for k in ("id", "name", "telegram", "lang", "city", "role", "level", "years",
                                     "goal", "company", "looks_like", "about")},
                "stack": ";".join(r["stack"]),
                "interests": ";".join(r["interests"]),
                "target_roles": ";".join(t["roles"]),
                "target_skills": ";".join(t["skills"]),
                "target_level": t["level"] or "",
                "target_domains": ";".join(t["domains"]),
                "openings": json.dumps(r["openings"], ensure_ascii=False) if r["openings"] else "",
            })
    print(f"{len(profiles)} анкет → {DATA / 'profiles.json'}, {DATA / 'profiles.csv'}")


if __name__ == "__main__":
    main()
