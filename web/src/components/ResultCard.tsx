import { ArrowLeftRight, Check, Clock, Copy, Handshake, MapPin, MessageCircle, Radio, Send, ThumbsDown, TriangleAlert, UserRound } from "lucide-react";
import { useId, useState, type CSSProperties } from "react";
import { beaconInk, hue, initials } from "./ink";
import type { IntroView, Reason, Recommendation } from "../api";
import type { Strings, TextKey } from "../i18n";

const RADIUS = 24;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function ScoreRing({ score, label }: { score: number; label: string }) {
  const gradientId = useId();
  return (
    <div className="score" role="img" aria-label={`${score}% ${label}`}>
      <svg viewBox="0 0 56 56" aria-hidden>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--accent-from)" />
            <stop offset="100%" stopColor="var(--accent-to)" />
          </linearGradient>
        </defs>
        <circle className="score__track" cx="28" cy="28" r={RADIUS} />
        <circle
          className="score__value"
          cx="28"
          cy="28"
          r={RADIUS}
          stroke={`url(#${gradientId})`}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - score / 100)}
        />
      </svg>
      <span className="score__text">
        {score}
        <small>%</small>
      </span>
    </div>
  );
}

interface Props {
  rec: Recommendation;
  t: Strings;
  index: number;
  /** Отзыв о человеке; пока идёт пересчёт, кнопки неактивны. */
  onMet: () => void;
  onNotFit: (reason: Reason) => void;
  busy: boolean;
  intro?: IntroView;
  onWantMeet: () => void;
  onOpenBeacon: () => void;
}

const REASONS: [Reason, TextKey][] = [
  ["level", "reasonLevel"],
  ["stack", "reasonStack"],
  ["domain", "reasonDomain"],
  ["other", "reasonOther"],
];

export function ResultCard({ rec, t, index, onMet, onNotFit, busy, intro, onWantMeet, onOpenBeacon }: Props) {
  const { candidate: c, explanation: e } = rec;
  const [copied, setCopied] = useState(false);
  const [choosingReason, setChoosingReason] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(e.icebreaker);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Буфер обмена недоступен (не HTTPS): фраза и так видна на экране.
    }
  };

  const chipGroups: [keyof typeof e.shared, string][] = [
    ["stack", t.chipStack],
    ["topics", t.chipTopics],
    ["domain", t.chipDomain],
  ];
  const style = { "--hue": hue(c.name), animationDelay: `${index * 60}ms` } as CSSProperties;

  return (
    <article className={rec.weak ? "result is-weak" : "result"} style={style}>
      <header className="result__head">
        <div className="avatar" aria-hidden>{initials(c.name)}</div>
        <div className="result__who">
          <h3>{c.name}</h3>
          <p className="result__meta">
            {c.role_label} · {c.level_label}
            {c.company ? <> · <strong>{c.company}</strong></> : null}
          </p>
          <div className="result__badges">
            <span className="badge">{c.goal_label}</span>
            <span className="badge badge--plain">
              <MapPin size={12} aria-hidden /> {c.city}
            </span>
            {rec.weak && <span className="badge badge--muted">{t.weak}</span>}
          </div>
        </div>
        <ScoreRing score={rec.score} label={t.match} />
      </header>

      <div className="why">
        <div className="why__row">
          <span className="why__icon" aria-hidden><UserRound size={15} /></span>
          <div>
            <span className="why__label">{e.label_you}</span>
            <p>{e.for_me}</p>
          </div>
        </div>
        <div className="why__row">
          <span className="why__icon why__icon--mutual" aria-hidden><ArrowLeftRight size={15} /></span>
          <div>
            <span className="why__label">{e.label_them}</span>
            <p>{e.for_them}</p>
          </div>
        </div>
      </div>

      {chipGroups.some(([kind]) => e.shared[kind]?.length) && (
        <div className="shared">
          {chipGroups.map(([kind, label]) =>
            e.shared[kind]?.length ? (
              <div className="shared__group" key={kind}>
                <span className="shared__label">{label}</span>
                {e.shared[kind]!.map((item) => <span className="pill" key={item}>{item}</span>)}
              </div>
            ) : null,
          )}
        </div>
      )}

      {e.warnings.length > 0 && (
        <p className="alert alert--warn">
          <TriangleAlert size={15} aria-hidden /> {e.warnings.join("; ")}
        </p>
      )}

      <figure className="icebreaker">
        <figcaption>
          <MessageCircle size={14} aria-hidden /> {t.icebreaker}
        </figcaption>
        <blockquote>{e.icebreaker}</blockquote>
        <button type="button" className="icon-button" onClick={copy} aria-label={copied ? t.copied : t.copy}
                title={copied ? t.copied : t.copy}>
          {copied ? <Check size={16} aria-hidden /> : <Copy size={16} aria-hidden />}
        </button>
      </figure>

      <div className="meet">
        {!intro && (
          <button type="button" className="meet__button" onClick={onWantMeet} disabled={busy}>
            <Send size={16} aria-hidden /> {t.wantMeet}
          </button>
        )}
        {intro?.status === "pending" && (
          <span className="meet__status"><Clock size={15} aria-hidden /> {t.requestSent}</span>
        )}
        {intro?.status === "accepted" && (
          <>
            <button type="button" className="meet__button meet__button--beacon" onClick={onOpenBeacon}
                    style={{ ["--beacon" as string]: intro.beacon?.color, ["--beacon-ink" as string]: beaconInk(intro.beacon?.color) }}>
              <Radio size={16} aria-hidden /> {t.openBeacon} · {intro.beacon?.code} · {intro.beacon?.time}
            </button>
            <span className="meet__status meet__status--ok">
              <Check size={15} aria-hidden /> {t.matched}{intro.simulated ? ` (${t.simulatedNote})` : ""}
            </span>
          </>
        )}
      </div>

      <footer className="feedback">
        {choosingReason ? (
          <div className="feedback__reasons" role="group" aria-label={t.whatsOff}>
            <span className="feedback__question">{t.whatsOff}</span>
            {REASONS.map(([reason, label]) => (
              <button type="button" key={reason} className="chip" disabled={busy} onClick={() => onNotFit(reason)}>
                {t[label]}
              </button>
            ))}
            <button type="button" className="ghost-button" onClick={() => setChoosingReason(false)}>
              {t.cancel}
            </button>
          </div>
        ) : (
          <>
            <button type="button" className="feedback__button feedback__button--met" disabled={busy} onClick={onMet}>
              <Handshake size={16} aria-hidden /> {t.met}
            </button>
            <button type="button" className="feedback__button" disabled={busy} onClick={() => setChoosingReason(true)}>
              <ThumbsDown size={16} aria-hidden /> {t.notFit}
            </button>
          </>
        )}
      </footer>
    </article>
  );
}

export function ResultSkeleton() {
  return (
    <div className="result result--skeleton" aria-hidden>
      <div className="result__head">
        <div className="avatar skeleton" />
        <div className="result__who">
          <div className="skeleton skeleton--line" style={{ width: "40%" }} />
          <div className="skeleton skeleton--line" style={{ width: "65%" }} />
        </div>
      </div>
      <div className="skeleton skeleton--block" />
    </div>
  );
}
