"""Тексты Telegram-бота на трёх языках. Казахские строки стоит вычитать носителю."""

from kopir.taxonomy import Lang

TEXTS: dict[Lang, dict[str, str]] = {
    "ru": {
        "greeting": (
            "Сәлем! Я <b>Kópir</b> — помогаю на IT-мероприятиях знакомиться с теми, кому вы тоже полезны.\n\n"
            "Нажмите «Открыть Kópir», заполните анкету за минуту — и получите 5 человек "
            "с объяснением, почему вам стоит познакомиться."
        ),
        "open": "Открыть Kópir",
        "no_app": "Приложение скоро откроется прямо здесь, в Telegram.",
        "help": (
            "/start — открыть Kópir\n/help — помощь\n\n"
            "Все анкеты в демо вымышленные."
        ),
        "fallback": "Я понимаю кнопки и команды. Нажмите «Открыть Kópir» 👇",
        "cmd_start": "Открыть Kópir",
        "cmd_help": "Помощь",
    },
    "kk": {
        "greeting": (
            "Сәлем! Мен <b>Kópir</b> — IT-іс-шараларда сізге де пайдалы адамдармен танысуға көмектесемін.\n\n"
            "«Kópir-ді ашу» батырмасын басып, бір минутта сауалнаманы толтырыңыз — танысуға тұрарлық "
            "5 адамды түсіндірмесімен бірге аласыз."
        ),
        "open": "Kópir-ді ашу",
        "no_app": "Қосымша жақында осы жерде, Telegram-да ашылады.",
        "help": (
            "/start — Kópir-ді ашу\n/help — көмек\n\n"
            "Демодағы барлық сауалнамалар ойдан шығарылған."
        ),
        "fallback": "Мен батырмалар мен командаларды түсінемін. «Kópir-ді ашу» батырмасын басыңыз 👇",
        "cmd_start": "Kópir-ді ашу",
        "cmd_help": "Көмек",
    },
    "en": {
        "greeting": (
            "Hi! I'm <b>Kópir</b> — I help you meet people at IT events who benefit from knowing you too.\n\n"
            "Tap “Open Kópir”, fill in a one-minute profile and get 5 people "
            "with an explanation of why you should meet."
        ),
        "open": "Open Kópir",
        "no_app": "The app will soon open right here in Telegram.",
        "help": "/start — open Kópir\n/help — help\n\nAll profiles in the demo are fictional.",
        "fallback": "I understand buttons and commands. Tap “Open Kópir” 👇",
        "cmd_start": "Open Kópir",
        "cmd_help": "Help",
    },
}
