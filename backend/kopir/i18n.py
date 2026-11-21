"""Мелкие языковые помощники для RU / KK / EN: длительность опыта и перечисления."""

from collections.abc import Sequence

from kopir.taxonomy import Lang

_CONJUNCTION: dict[Lang, str] = {"ru": "и", "kk": "және", "en": "and"}


def _decimal(n: float) -> str:
    """Дробная часть через запятую, как принято в русском и казахском: 7,5."""
    return f"{n:g}".replace(".", ",")


def _years_ru(n: float) -> str:
    if n < 1:
        return "меньше года"
    if n != int(n):
        return f"{_decimal(n)} года"
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        word = "год"
    elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        word = "года"
    else:
        word = "лет"
    return f"{n} {word}"


def _years_kk(n: float) -> str:
    return "бір жылдан аз" if n < 1 else f"{_decimal(n)} жыл"


def _years_en(n: float) -> str:
    return "under a year" if n < 1 else f"{n:g} year{'s' if n != 1 else ''}"


_YEARS = {"ru": _years_ru, "kk": _years_kk, "en": _years_en}


def years(n: float, lang: Lang) -> str:
    """«3 года», «3 жыл», «3 years»."""
    return _YEARS[lang](n)


def join(items: Sequence[str], lang: Lang) -> str:
    """«A, B и C», «A, B және C», «A, B and C»."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} {_CONJUNCTION[lang]} {items[-1]}"
