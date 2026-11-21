import pytest

from kopir.i18n import join, years


@pytest.mark.parametrize(
    ("n", "lang", "expected"),
    [
        (1, "ru", "1 год"), (3, "ru", "3 года"), (5, "ru", "5 лет"), (11, "ru", "11 лет"),
        (21, "ru", "21 год"), (7.5, "ru", "7,5 года"), (0.5, "ru", "меньше года"),
        (7.5, "kk", "7,5 жыл"), (0.5, "kk", "бір жылдан аз"),
        (1, "en", "1 year"), (7.5, "en", "7.5 years"),
    ],
)
def test_years(n, lang, expected):
    assert years(n, lang) == expected


@pytest.mark.parametrize(
    ("items", "lang", "expected"),
    [([], "ru", ""), (["Go"], "ru", "Go"), (["Go", "Rust"], "kk", "Go және Rust"),
     (["A", "B", "C"], "en", "A, B and C")],
)
def test_join(items, lang, expected):
    assert join(items, lang) == expected
