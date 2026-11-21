// Запуск внутри Telegram как Mini App — без внешнего скрипта telegram-web-app.js.
//
// Telegram передаёт параметры запуска во фрагменте адреса (#tgWebAppData=…),
// а команды принимает через документированный протокол событий:
// TelegramWebviewProxy.postEvent в мобильных клиентах и postMessage в веб-клиенте
// (https://core.telegram.org/api/web-events). Вне Telegram модуль ничего не делает.
//
// Данные пользователя здесь используются только для удобства (имя, язык) и не
// проверяются: всё, что требует доверия, сервер должен проверять по подписи initData.

import { LANGS, type Lang } from "./api";

interface TelegramUser {
  first_name?: string;
  last_name?: string;
  language_code?: string;
}

export interface TelegramLaunch {
  user: TelegramUser | null;
  colorScheme: "light" | "dark" | null;
}

const STORAGE_KEY = "kopir.tg-launch";

function parseJson<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/** Тёмная ли тема Telegram — по яркости цвета фона (#rrggbb). */
function schemeOf(bg: string | undefined): "light" | "dark" | null {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(bg ?? "");
  if (!m) return null;
  const [r, g, b] = m.slice(1).map((h) => parseInt(h, 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b < 128 ? "dark" : "light";
}

function readFromHash(): TelegramLaunch | null {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const data = params.get("tgWebAppData");
  if (!data) return null;
  const theme = parseJson<{ bg_color?: string }>(params.get("tgWebAppThemeParams"));
  return {
    user: parseJson<TelegramUser>(new URLSearchParams(data).get("user")),
    colorScheme: schemeOf(theme?.bg_color),
  };
}

/** Параметры запуска; после перезагрузки страницы фрагмента уже нет — берём сохранённые. */
export function readLaunch(): TelegramLaunch | null {
  const fromHash = readFromHash();
  try {
    if (fromHash) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(fromHash));
    return fromHash ?? parseJson<TelegramLaunch>(sessionStorage.getItem(STORAGE_KEY));
  } catch {
    return fromHash;
  }
}

type TelegramWindow = Window & { TelegramWebviewProxy?: { postEvent: (type: string, data: string) => void } };

function postEvent(type: string, data: Record<string, unknown> = {}): void {
  const w = window as TelegramWindow;
  if (w.TelegramWebviewProxy) {
    w.TelegramWebviewProxy.postEvent(type, JSON.stringify(data));
  } else if (window.parent !== window) {
    window.parent.postMessage(JSON.stringify({ eventType: type, eventData: data }), "https://web.telegram.org");
  }
}

/** Сообщить Telegram, что приложение готово, и развернуть его на весь экран. */
export function announceReady(): void {
  postEvent("web_app_ready");
  postEvent("web_app_expand");
}

export function langOf(launch: TelegramLaunch | null): Lang | null {
  const code = launch?.user?.language_code?.split("-")[0].toLowerCase();
  return code && (LANGS as string[]).includes(code) ? (code as Lang) : null;
}

/** «Айгерім Сәрсенова» → «Айгерім С.» — как в анкетах зала. */
export function displayName(launch: TelegramLaunch | null): string {
  const first = launch?.user?.first_name?.trim();
  if (!first) return "";
  const last = launch?.user?.last_name?.trim();
  return last ? `${first} ${last[0]}.` : first;
}
