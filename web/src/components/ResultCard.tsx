import { useState } from "react";
import type { Recommendation } from "../api";
import type { Strings } from "../i18n";

const RADIUS = 22;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function ScoreRing({ score, label }: { score: number; label: string }) {
  return (
    <div className="score" role="img" aria-label={`${score}% ${label}`}>
      <svg viewBox="0 0 52 52" aria-hidden>
        <circle className="score__track" cx="26" cy="26" r={RADIUS} />
        <circle
          className="score__value"
          cx="26"
          cy="26"
          r={RADIUS}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - score / 100)}
        />
      </svg>
      <span>{score}%</span>
    </div>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

interface Props {
  rec: Recommendation;
  t: Strings;
}

export function ResultCard({ rec, t }: Props) {
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

  return (
    <article className={rec.weak ? "result is-weak" : "result"}>
      <header className="result__head">
        <div className="avatar" aria-hidden>{initials(c.name)}</div>
        <div className="result__who">
          <h3>{c.name}</h3>
          <p>
            {c.role_label} · {c.level_label}
            {c.company ? ` · ${c.company}` : ""} · {c.city}
          </p>
          <span className="badge">{c.goal_label}</span>
          {rec.weak && <span className="badge badge--muted">{t.weak}</span>}
        </div>
        <ScoreRing score={rec.score} label={t.match} />
      </header>

      <dl className="why">
        <div>
          <dt>{e.label_you}</dt>
          <dd>{e.for_me}</dd>
        </div>
        <div>
          <dt>{e.label_them}</dt>
          <dd>{e.for_them}</dd>
        </div>
      </dl>

      {chipGroups.some(([kind]) => e.shared[kind]?.length) && (
        <div className="shared">
          {chipGroups.map(([kind, label]) =>
            e.shared[kind]?.length ? (
              <div className="shared__group" key={kind}>
                <span className="shared__label">{label}</span>
                {e.shared[kind]!.map((item) => (
                  <span className="tag tag--static" key={item}>{item}</span>
                ))}
              </div>
            ) : null,
          )}
        </div>
      )}

      {e.warnings.length > 0 && (
        <p className="warning">⚠ {e.warnings.join("; ")}</p>
      )}

      <div className="icebreaker">
        <span className="icebreaker__label">💬 {t.icebreaker}</span>
        <p>{e.icebreaker}</p>
        <button type="button" className="link-button" onClick={copy}>
          {copied ? t.copied : t.copy}
        </button>
      </div>
    </article>
  );
}
