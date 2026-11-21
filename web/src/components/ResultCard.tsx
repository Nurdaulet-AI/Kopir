import { ArrowLeftRight, Check, Copy, MapPin, MessageCircle, TriangleAlert, UserRound } from "lucide-react";
import { useId, useState, type CSSProperties } from "react";
import type { Recommendation } from "../api";
import type { Strings } from "../i18n";

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

// Аватары — в холодной гамме бренда (бирюза → синий → фиолетовый): тёплые
// оттенки вроде красного читаются как ошибка.
const HUE_FROM = 175;
const HUE_SPAN = 105;

/** Стабильный оттенок аватара из имени: у человека всегда один цвет. */
function hue(name: string): number {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % HUE_SPAN;
  return HUE_FROM + h;
}

function initials(name: string): string {
  return name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

interface Props {
  rec: Recommendation;
  t: Strings;
  index: number;
}

export function ResultCard({ rec, t, index }: Props) {
  const { candidate: c, explanation: e } = rec;
  const [copied, setCopied] = useState(false);

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
