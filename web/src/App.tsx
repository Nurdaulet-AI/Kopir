import { ArrowLeft, ArrowLeftRight, Languages, LoaderCircle, ShieldCheck, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, LANGS, type Lang, type Options, type ProfileInput, type Recommendation } from "./api";
import { LangSwitch, ThemeSwitch, type Theme } from "./components/Controls";
import { ProfileForm } from "./components/ProfileForm";
import { ResultCard, ResultSkeleton } from "./components/ResultCard";
import { format, STRINGS, type Strings } from "./i18n";
import { EMPTY_DRAFT, example, toProfile, validate, type Draft } from "./profile";

const PAGE = 5;
// Сервер отдаёт не больше 20 рекомендаций за запрос.
const MAX_K = 20;
const THEMES: Theme[] = ["light", "dark", "system"];

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

function loadChoice<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  const stored = load<string>(key, fallback);
  return allowed.includes(stored as T) ? (stored as T) : fallback;
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

function BrandMark() {
  return (
    <svg className="brand__mark" viewBox="0 0 36 36" aria-hidden>
      <defs>
        <linearGradient id="brand-gradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--accent-from)" />
          <stop offset="100%" stopColor="var(--accent-to)" />
        </linearGradient>
      </defs>
      <rect width="36" height="36" rx="10" fill="url(#brand-gradient)" />
      <path d="M8 23c4.2-8.7 15.8-8.7 20 0" stroke="var(--gold)" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M11.5 22.5v4.5M24.5 22.5v4.5" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [lang, setLang] = useState<Lang>(() => loadChoice("kopir.lang", LANGS, "ru"));
  const [theme, setTheme] = useState<Theme>(() => loadChoice("kopir.theme", THEMES, "system"));
  const [options, setOptions] = useState<Options | null>(null);
  const [draft, setDraft] = useState<Draft>(() => ({ ...EMPTY_DRAFT, ...load<Partial<Draft>>("kopir.draft", {}) }));
  const [results, setResults] = useState<Results | null>(null);
  const [pending, setPending] = useState(false);
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

  useEffect(() => {
    save("kopir.theme", theme);
    const root = document.documentElement;
    if (theme === "system") delete root.dataset.theme;
    else root.dataset.theme = theme;
  }, [theme]);

  useEffect(() => save("kopir.draft", draft), [draft]);

  const run = useCallback(
    async (profile: ProfileInput, opts: { exclude?: string[]; append?: boolean } = {}) => {
      setBusy(true);
      setError(null);
      if (!opts.append) {
        setPending(true);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      try {
        const res = await api.recommend({ profile, lang, k: PAGE, exclude: opts.exclude ?? [] });
        setResults((prev) => ({
          profile,
          items: opts.append && prev ? [...prev.items, ...res.recommendations] : res.recommendations,
          elapsedMs: res.elapsed_ms,
          exhausted: res.recommendations.length < PAGE,
        }));
      } catch (e) {
        setError(errorText(e, t));
      } finally {
        setBusy(false);
        setPending(false);
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

  const showResults = pending || results !== null;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__inner">
          <div className="brand">
            <BrandMark />
            <span className="brand__name">Kópir</span>
          </div>
          <div className="topbar__controls">
            <LangSwitch value={lang} onChange={changeLang} />
            <ThemeSwitch value={theme} onChange={setTheme} t={t} />
          </div>
        </div>
      </header>

      <main className="container">
        {!showResults && (
          <section className="hero">
            <h1>{t.tagline}</h1>
            <p className="hero__subtitle">{t.heroSubtitle}</p>
            <ul className="hero__features">
              <li><ArrowLeftRight size={15} aria-hidden /> {t.featureMutual}</li>
              <li><Languages size={15} aria-hidden /> RU · ҚАЗ · EN</li>
              <li><Zap size={15} aria-hidden /> {t.featureFast}</li>
            </ul>
            <p className="hero__note"><ShieldCheck size={14} aria-hidden /> {t.syntheticNote}</p>
          </section>
        )}

        {!options && !error && (
          <p className="loading"><LoaderCircle size={18} className="spin" aria-hidden /></p>
        )}
        {!options && error && <p className="alert alert--error" role="alert">{error}</p>}

        {options && !showResults && (
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

        {options && showResults && (
          <section className="results" aria-busy={pending}>
            <button type="button" className="ghost-button ghost-button--back" onClick={() => setResults(null)}>
              <ArrowLeft size={16} aria-hidden /> {t.editProfile}
            </button>
            <h1>{t.resultsTitle}</h1>
            <p className="results__subtitle">{t.resultsSubtitle}</p>
            {results && !pending && (
              <p className="results__meta">
                <Zap size={14} aria-hidden /> {format(t.matchedIn, { ms: Math.max(1, Math.round(results.elapsedMs)) })}
              </p>
            )}
            <div className="results__list">
              {pending
                ? Array.from({ length: PAGE }, (_, i) => <ResultSkeleton key={i} />)
                : results?.items.map((rec, i) => (
                    <ResultCard key={rec.candidate.id} rec={rec} t={t} index={i % PAGE} />
                  ))}
            </div>
            {error && <p className="alert alert--error" role="alert">{error}</p>}
            {results && !pending && (results.exhausted ? (
              <p className="results__end">{t.noMore}</p>
            ) : (
              <button type="button" className="secondary-button" onClick={showMore} disabled={busy}>
                {busy ? <LoaderCircle size={16} className="spin" aria-hidden /> : null}
                {busy ? t.searching : t.showMore}
              </button>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}
