import { ArrowLeft, ArrowLeftRight, Handshake, Languages, LoaderCircle, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  ApiError,
  LANGS,
  type Feedback,
  type Lang,
  type Options,
  type ProfileInput,
  type Reason,
  type Recommendation,
} from "./api";
import { LangSwitch, ThemeSwitch, type Theme } from "./components/Controls";
import { ShanyraqMark } from "./components/Logo";
import { ProfileForm } from "./components/ProfileForm";
import { ResultCard, ResultSkeleton } from "./components/ResultCard";
import { format, STRINGS, type Strings, type TextKey } from "./i18n";
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
  /** Все отзывы по этой анкете: сервер исключает этих людей и меняет личные веса. */
  feedback: Feedback[];
  met: Recommendation[];
  lastFeedback: Feedback | null;
}

// Что стало важнее после «не подошло» — для подсказки над выдачей.
const REASON_TEXT: Record<Exclude<Reason, "other">, TextKey> = {
  level: "whatLevel",
  stack: "whatStack",
  domain: "whatDomain",
};

function feedbackNotice(f: Feedback | null, t: Strings): string | null {
  if (f === null) return null;
  if (f.verdict === "not_fit" && f.reason !== "other") {
    return `${t.feedbackApplied} ${format(t.nowMatters, { what: t[REASON_TEXT[f.reason]] })}`;
  }
  return t.feedbackApplied;
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

  const request = (profile: ProfileInput, l: Lang, feedback: Feedback[], k: number, exclude: string[] = []) =>
    api.recommend({ profile, lang: l, k, exclude, feedback });

  const guarded = useCallback(
    async (job: () => Promise<void>, l: Lang) => {
      setBusy(true);
      setError(null);
      try {
        await job();
      } catch (e) {
        setError(errorText(e, STRINGS[l]));
      } finally {
        setBusy(false);
        setPending(false);
      }
    },
    [],
  );

  const submit = () => {
    const problem = validate(draft);
    if (problem) {
      setError(t[problem]);
      return;
    }
    const profile = toProfile(draft, lang);
    setPending(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
    void guarded(async () => {
      const res = await request(profile, lang, [], PAGE);
      setResults({
        profile, items: res.recommendations, elapsedMs: res.elapsed_ms, exhausted: res.recommendations.length < PAGE,
        feedback: [], met: [], lastFeedback: null,
      });
    }, lang);
  };

  const showMore = () => {
    if (!results) return;
    void guarded(async () => {
      const seen = results.items.map((r) => r.candidate.id);
      const res = await request(results.profile, lang, results.feedback, PAGE, seen);
      setResults({
        ...results, items: [...results.items, ...res.recommendations], elapsedMs: res.elapsed_ms,
        exhausted: res.recommendations.length < PAGE,
      });
    }, lang);
  };

  /** Отзыв: человек уходит из выдачи, подборка того же размера пересчитывается с новыми весами. */
  const giveFeedback = (rec: Recommendation, item: Feedback) => {
    if (!results) return;
    const feedback = [...results.feedback, item];
    const k = Math.min(Math.max(results.items.length, PAGE), MAX_K);
    void guarded(async () => {
      const res = await request(results.profile, lang, feedback, k);
      setResults({
        ...results, items: res.recommendations, elapsedMs: res.elapsed_ms, exhausted: res.recommendations.length < k,
        feedback, met: item.verdict === "met" ? [...results.met, rec] : results.met, lastFeedback: item,
      });
    }, lang);
  };

  const changeLang = (next: Lang) => {
    setLang(next);
    // Объяснения строит сервер на нужном языке — перезапрашиваем показанное.
    if (!results) return;
    const profile = { ...results.profile, lang: next };
    void guarded(async () => {
      const res = await request(profile, next, results.feedback, Math.min(Math.max(results.items.length, 1), MAX_K));
      setResults({ ...results, profile, items: res.recommendations });
    }, next);
  };

  const showResults = pending || results !== null;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__inner">
          <div className="brand">
            <ShanyraqMark />
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
            {results && !pending && feedbackNotice(results.lastFeedback, t) && (
              <p className="notice" role="status">
                <Sparkles size={15} aria-hidden /> {feedbackNotice(results.lastFeedback, t)}
              </p>
            )}
            {results && results.met.length > 0 && (
              <div className="met">
                <span className="met__title"><Handshake size={15} aria-hidden /> {t.metTitle}</span>
                {results.met.map((r) => (
                  <span className="pill" key={r.candidate.id}>{r.candidate.name} · {r.candidate.role_label}</span>
                ))}
              </div>
            )}
            <div className="results__list">
              {pending
                ? Array.from({ length: PAGE }, (_, i) => <ResultSkeleton key={i} />)
                : results?.items.map((rec, i) => (
                    <ResultCard
                      key={rec.candidate.id}
                      rec={rec}
                      t={t}
                      index={i % PAGE}
                      busy={busy}
                      onMet={() => giveFeedback(rec, { candidate_id: rec.candidate.id, verdict: "met" })}
                      onNotFit={(reason) => giveFeedback(rec, { candidate_id: rec.candidate.id, verdict: "not_fit", reason })}
                    />
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
