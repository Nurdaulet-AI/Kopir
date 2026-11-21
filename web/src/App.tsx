import { ArrowLeft, ArrowLeftRight, BellRing, CalendarClock, Check, Handshake, Radio, Languages, LayoutDashboard, LoaderCircle, ShieldCheck, Sparkles, UserRound, Zap } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  LANGS,
  type Feedback,
  type IntroView,
  type Lang,
  type Options,
  type ProfileInput,
  type Reason,
  type Recommendation,
  type Squad,
} from "./api";
import { Beacon } from "./components/Beacon";
import { LangSwitch, ThemeSwitch, type Theme } from "./components/Controls";
import { ShanyraqMark } from "./components/Logo";
import { OrganizerDashboard } from "./components/OrganizerDashboard";
import { ProfileForm } from "./components/ProfileForm";
import { ResultCard, ResultSkeleton } from "./components/ResultCard";
import { SquadCard } from "./components/SquadCard";
import { beaconInk } from "./components/ink";
import { format, STRINGS, type Strings, type TextKey } from "./i18n";
import { EMPTY_DRAFT, example, toProfile, validate, type Draft } from "./profile";
import { announceReady, displayName, langOf, readLaunch } from "./telegram";

const PAGE = 5;
// Сервер отдаёт не больше 20 рекомендаций за запрос.
const MAX_K = 20;
const THEMES: Theme[] = ["light", "dark", "system"];
// Открыты ли мы как Mini App внутри Telegram (иначе null).
const TELEGRAM = readLaunch();

type View = "participant" | "organizer";
// Экран — в адресе (?view=organizer), чтобы дашборд открывался прямой ссылкой, например на проекторе.
const initialView = (): View => (new URLSearchParams(window.location.search).get("view") === "organizer" ? "organizer" : "participant");

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
  // Явный выбор пользователя важнее подсказок Telegram: язык и тема клиента — только по умолчанию.
  const [lang, setLang] = useState<Lang>(() => loadChoice("kopir.lang", LANGS, langOf(TELEGRAM) ?? "ru"));
  const [theme, setTheme] = useState<Theme>(() => loadChoice("kopir.theme", THEMES, TELEGRAM?.colorScheme ?? "system"));
  const [options, setOptions] = useState<Options | null>(null);
  const [draft, setDraft] = useState<Draft>(() => {
    const saved = { ...EMPTY_DRAFT, ...load<Partial<Draft>>("kopir.draft", {}) };
    return saved.name ? saved : { ...saved, name: displayName(TELEGRAM) };
  });
  const [results, setResults] = useState<Results | null>(null);
  const [pending, setPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>(initialView);
  // Знакомства: id в зале появляется при первом «Хочу познакомиться».
  const [profileId, setProfileId] = useState<string | null>(null);
  const [intros, setIntros] = useState<IntroView[]>([]);
  const [beacon, setBeacon] = useState<IntroView | null>(null);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);
  const [squad, setSquad] = useState<Squad | null>(null);
  const joining = useRef<Promise<string> | null>(null);
  const seen = useRef(new Map<string, string>());
  const [agreed, setAgreed] = useState<string | null>(null);
  const t = STRINGS[lang];

  const changeView = (next: View) => {
    setView(next);
    const url = new URL(window.location.href);
    if (next === "organizer") url.searchParams.set("view", "organizer");
    else url.searchParams.delete("view");
    window.history.replaceState(null, "", url);
    window.scrollTo({ top: 0 });
  };

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

  useEffect(() => {
    if (TELEGRAM) announceReady();
  }, []);

  // Опрос входящих запросов и подтверждений: на мероприятии хватает раза в 4 секунды.
  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    const tick = () => api.intros(profileId, lang).then((list) => {
      if (cancelled) return;
      // Ответ пришёл: показываем маячок один раз — там, где согласие получено только что.
      const fresh = list.find((i) => i.status === "accepted" && seen.current.get(i.id) === "pending");
      list.forEach((i) => seen.current.set(i.id, i.status));
      setIntros(list);
      if (fresh) {
        setAgreed(format(STRINGS[lang].agreed, { name: fresh.other.name }));
        setBeacon(fresh);
      }
    }, () => undefined);
    void tick();
    const timer = window.setInterval(tick, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [profileId, lang]);

  const upsertIntro = (intro: IntroView) => {
    if (!seen.current.has(intro.id)) seen.current.set(intro.id, intro.status);
    setIntros((list) => [intro, ...list.filter((i) => i.id !== intro.id)]);
  };

  /** Анкета попадает в зал один раз — при первом запросе на знакомство. */
  const ensureJoined = (profile: ProfileInput): Promise<string> => {
    if (profileId) return Promise.resolve(profileId);
    joining.current ??= api.join(profile).then((r) => {
      setProfileId(r.profile_id);
      return r.profile_id;
    });
    return joining.current;
  };

  const wantMeet = (rec: Recommendation) => {
    if (!results) return;
    void guarded(async () => {
      const me = await ensureJoined(results.profile);
      const intro = await api.intro(me, rec.candidate.id, lang);
      upsertIntro(intro);
      if (intro.status === "accepted") setBeacon(intro); // встречный запрос: согласие уже есть
    }, lang);
  };

  /** «Позвать всех»: запрос на знакомство каждому участнику группы (то же двойное согласие). */
  const inviteSquad = () => {
    if (!results || !squad) return;
    void guarded(async () => {
      const me = await ensureJoined(results.profile);
      const group = `g${Date.now()}`;
      for (const m of squad.members) upsertIntro(await api.intro(me, m.id, lang, group));
    }, lang);
  };

  const answer = (intro: IntroView, accept: boolean) => {
    if (!profileId) return;
    void guarded(async () => {
      const updated = await api.respond(intro.id, profileId, accept, lang);
      upsertIntro(updated);
      if (updated.status === "accepted") setBeacon(updated);
    }, lang);
  };

  /** Голосовая анкета: текст дописывается в «о себе», распознанные поля заполняют пустые места формы. */
  const fillFromVoice = (text: string) => {
    void guarded(async () => {
      const parsed = await api.parse(text);
      setDraft((d) => {
        const merge = (a: string[], b: string[]) => [...a, ...b.filter((x) => !a.includes(x))];
        return {
          ...d,
          about: d.about ? `${d.about} ${text}` : text,
          role: parsed.role ?? d.role,
          level: parsed.level ?? d.level,
          years: parsed.years ?? d.years,
          goal: d.goal ?? parsed.goal,
          stack: merge(d.stack, parsed.stack),
          interests: merge(d.interests, parsed.interests),
        };
      });
      setVoiceNotice(t.voiceFilled);
    }, lang);
  };

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
    // Новая анкета — новое место в зале: прежние запросы относятся к старой версии.
    setProfileId(null);
    setIntros([]);
    setAgreed(null);
    seen.current.clear();
    joining.current = null;
    setPending(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
    setSquad(null);
    // Группа — дополнение к подборке: её ошибка не мешает основному ответу.
    api.squad(profile, lang).then(setSquad, () => setSquad(null));
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
            <div className="segmented segmented--nav" role="group" aria-label="Kópir">
              <button type="button" aria-pressed={view === "participant"} onClick={() => changeView("participant")}>
                <UserRound size={15} aria-hidden /> <span>{t.viewParticipant}</span>
              </button>
              <button type="button" aria-pressed={view === "organizer"} onClick={() => changeView("organizer")}>
                <LayoutDashboard size={15} aria-hidden /> <span>{t.viewOrganizer}</span>
              </button>
            </div>
            <LangSwitch value={lang} onChange={changeLang} />
            <ThemeSwitch value={theme} onChange={setTheme} t={t} />
          </div>
        </div>
      </header>

      <main className={view === "organizer" ? "container container--wide" : "container"}>
        {view === "organizer" && <OrganizerDashboard lang={lang} t={t} />}
        {view === "participant" && !showResults && (
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

        {view === "participant" && !options && !error && (
          <p className="loading"><LoaderCircle size={18} className="spin" aria-hidden /></p>
        )}
        {view === "participant" && !options && error && <p className="alert alert--error" role="alert">{error}</p>}

        {view === "participant" && options && !showResults && (
          <ProfileForm
            draft={draft}
            onChange={(patch) => setDraft((d) => ({ ...d, ...patch }))}
            onExample={() => draft.goal && setDraft(example(draft.goal, lang))}
            onVoiceText={fillFromVoice}
            lang={lang}
            notice={voiceNotice}
            onSubmit={submit}
            options={options}
            t={t}
            busy={busy}
            error={error}
          />
        )}

        {view === "participant" && options && showResults && (
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
            {agreed && !pending && (
              <p className="notice" role="status"><Check size={15} aria-hidden /> {agreed}</p>
            )}
            {intros.some((i) => i.status === "accepted" && i.beacon) && (
              <section className="meetings">
                <h2><CalendarClock size={17} aria-hidden /> {t.myMeetings}</h2>
                <ul>
                  {Array.from(new Map(intros.filter((i) => i.status === "accepted" && i.beacon)
                    .sort((a, b) => a.beacon!.time.localeCompare(b.beacon!.time))
                    .map((i) => [i.beacon!.code, i])).values()).map((i) => (
                    <li key={i.id}>
                      <span className="meetings__time">{i.beacon!.time}</span>
                      <span className="meetings__who">
                        {intros.filter((x) => x.beacon?.code === i.beacon!.code).map((x) => x.other.name).join(", ")}
                      </span>
                      <button type="button" className="meet__button meet__button--beacon" onClick={() => setBeacon(i)}
                              style={{ ["--beacon" as string]: i.beacon!.color, ["--beacon-ink" as string]: beaconInk(i.beacon!.color) }}>
                        <Radio size={15} aria-hidden /> {format(t.zone, { n: i.beacon!.zone })} · {i.beacon!.code}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {intros.filter((i) => i.direction === "incoming" && i.status === "pending").map((i) => (
              <div className="incoming" key={i.id} role="status">
                <BellRing size={18} aria-hidden />
                <span><b>{i.other.name}</b> · {i.other.role_label} — {t.incoming}</span>
                <button type="button" className="meet__button" onClick={() => answer(i, true)} disabled={busy}>
                  <Check size={15} aria-hidden /> {t.accept}
                </button>
                <button type="button" className="ghost-button" onClick={() => answer(i, false)} disabled={busy}>
                  {t.decline}
                </button>
              </div>
            ))}
            {results && results.met.length > 0 && (
              <div className="met">
                <span className="met__title"><Handshake size={15} aria-hidden /> {t.metTitle}</span>
                {results.met.map((r) => (
                  <span className="pill" key={r.candidate.id}>{r.candidate.name} · {r.candidate.role_label}</span>
                ))}
              </div>
            )}
            {squad && !pending && <SquadCard squad={squad} t={t} intros={intros} busy={busy} onInvite={inviteSquad} onOpenBeacon={setBeacon} />}
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
                      intro={intros.find((i) => i.other.id === rec.candidate.id && i.status !== "declined")}
                      onWantMeet={() => wantMeet(rec)}
                      onOpenBeacon={() => setBeacon(intros.find((i) => i.other.id === rec.candidate.id) ?? null)}
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
      {beacon && <Beacon intro={beacon} t={t} onClose={() => setBeacon(null)} />}
    </div>
  );
}
