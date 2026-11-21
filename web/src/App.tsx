import { useCallback, useEffect, useState } from "react";
import { api, ApiError, LANGS, type Lang, type Options, type ProfileInput, type Recommendation } from "./api";
import { LangSwitch } from "./components/LangSwitch";
import { ProfileForm } from "./components/ProfileForm";
import { ResultCard } from "./components/ResultCard";
import { format, STRINGS, type Strings } from "./i18n";
import { EMPTY_DRAFT, example, toProfile, validate, type Draft } from "./profile";

const PAGE = 5;
// Сервер отдаёт не больше 20 рекомендаций за запрос.
const MAX_K = 20;

// localStorage может быть недоступен (приватный режим): тогда просто не запоминаем.
function load<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // не запоминаем
  }
}

function initialLang(): Lang {
  const stored = load<string>("kopir.lang", "ru");
  return LANGS.includes(stored as Lang) ? (stored as Lang) : "ru";
}

function errorText(e: unknown, t: Strings): string {
  if (e instanceof ApiError) return e.status === 0 ? t.errorNetwork : e.message || t.errorGeneric;
  return t.errorGeneric;
}

interface Results {
  profile: ProfileInput;
  items: Recommendation[];
  elapsedMs: number;
  exhausted: boolean;
}

export default function App() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [options, setOptions] = useState<Options | null>(null);
  const [draft, setDraft] = useState<Draft>(() => ({ ...EMPTY_DRAFT, ...load<Partial<Draft>>("kopir.draft", {}) }));
  const [results, setResults] = useState<Results | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = STRINGS[lang];

  useEffect(() => {
    save("kopir.lang", lang);
    document.documentElement.lang = lang;
    let cancelled = false;
    api.options(lang).then(
      (o) => !cancelled && setOptions(o),
      (e) => !cancelled && setError(errorText(e, STRINGS[lang])),
    );
    return () => {
      cancelled = true;
    };
  }, [lang]);

  useEffect(() => save("kopir.draft", draft), [draft]);

  const run = useCallback(
    async (profile: ProfileInput, opts: { k?: number; exclude?: string[]; append?: boolean } = {}) => {
      setBusy(true);
      setError(null);
      try {
        const k = opts.k ?? PAGE;
        const res = await api.recommend({ profile, lang, k, exclude: opts.exclude ?? [] });
        setResults((prev) => ({
          profile,
          items: opts.append && prev ? [...prev.items, ...res.recommendations] : res.recommendations,
          elapsedMs: res.elapsed_ms,
          exhausted: res.recommendations.length < k,
        }));
        if (!opts.append) window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (e) {
        setError(errorText(e, t));
      } finally {
        setBusy(false);
      }
    },
    [lang, t],
  );

  const submit = () => {
    const problem = validate(draft);
    if (problem) {
      setError(t[problem]);
      return;
    }
    void run(toProfile(draft, lang));
  };

  const showMore = () => {
    if (!results) return;
    void run(results.profile, { exclude: results.items.map((r) => r.candidate.id), append: true });
  };

  const changeLang = (next: Lang) => {
    setLang(next);
    // Объяснения строит сервер на нужном языке — перезапрашиваем показанное.
    if (results) {
      const profile = { ...results.profile, lang: next };
      void api
        .recommend({ profile, lang: next, k: Math.min(results.items.length, MAX_K) })
        .then((res) => setResults({ ...results, profile, items: res.recommendations }))
        .catch((e) => setError(errorText(e, STRINGS[next])));
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden />
          <div>
            <span className="brand__name">Kópir</span>
            <span className="brand__tagline">{t.tagline}</span>
          </div>
        </div>
        <LangSwitch value={lang} onChange={changeLang} />
      </header>

      <p className="note">{t.syntheticNote}</p>

      <main>
        {!options && !error && <p className="loading">…</p>}
        {!options && error && <p className="error" role="alert">{error}</p>}

        {options && !results && (
          <ProfileForm
            draft={draft}
            onChange={(patch) => setDraft((d) => ({ ...d, ...patch }))}
            onExample={() => draft.goal && setDraft(example(draft.goal, lang))}
            onSubmit={submit}
            options={options}
            t={t}
            busy={busy}
            error={error}
          />
        )}

        {options && results && (
          <section className="results">
            <button type="button" className="link-button" onClick={() => setResults(null)}>
              {t.editProfile}
            </button>
            <h1>{t.resultsTitle}</h1>
            <p className="muted">{format(t.matchedIn, { ms: results.elapsedMs })}</p>
            {results.items.map((rec) => (
              <ResultCard key={rec.candidate.id} rec={rec} t={t} />
            ))}
            {error && <p className="error" role="alert">{error}</p>}
            {results.exhausted ? (
              <p className="muted">{t.noMore}</p>
            ) : (
              <button type="button" className="secondary" onClick={showMore} disabled={busy}>
                {busy ? t.searching : t.showMore}
              </button>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
