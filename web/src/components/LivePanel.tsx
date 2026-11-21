import { Check, Clock, LogIn, Radio, Send, UsersRound } from "lucide-react";
import type { CSSProperties } from "react";
import type { IntroView, LiveHall, LivePerson } from "../api";
import { format, type Strings } from "../i18n";
import { beaconInk, hue, initials } from "./ink";

interface Props {
  hall: LiveHall | null;
  joined: boolean;
  t: Strings;
  intros: IntroView[];
  busy: boolean;
  onJoin: () => void;
  onMeet: (candidateId: string) => void;
  onOpenBeacon: (intro: IntroView) => void;
}

function Person({ person, t, intro, busy, onMeet, onOpenBeacon }: {
  person: LivePerson; t: Strings; intro?: IntroView; busy: boolean;
  onMeet: () => void; onOpenBeacon: (intro: IntroView) => void;
}) {
  const c = person.candidate;
  return (
    <li className="live-person" style={{ "--hue": hue(c.name) } as CSSProperties}>
      <span className="avatar" aria-hidden>{initials(c.name)}</span>
      <div className="live-person__who">
        <b>{c.name}</b>
        <small>{c.role_label} · {c.level_label} · {c.goal_label}</small>
        {person.match && <p className="live-person__why">{person.match.explanation.for_me}</p>}
      </div>
      {person.match && <span className="live-person__score">{format(t.liveMatch, { n: person.match.score })}</span>}
      <div className="live-person__action">
        {!intro && (
          <button type="button" className="meet__button" onClick={onMeet} disabled={busy}>
            <Send size={15} aria-hidden /> {t.wantMeet}
          </button>
        )}
        {intro?.status === "pending" && intro.direction === "outgoing" && (
          <span className="meet__status"><Clock size={15} aria-hidden /> {t.requestSent}</span>
        )}
        {intro?.status === "accepted" && intro.beacon && (
          <button type="button" className="meet__button meet__button--beacon" onClick={() => onOpenBeacon(intro)}
                  style={{ "--beacon": intro.beacon.color, "--beacon-ink": beaconInk(intro.beacon.color) } as CSSProperties}>
            <Radio size={15} aria-hidden /> {intro.beacon.code} · {intro.beacon.time}
          </button>
        )}
      </div>
    </li>
  );
}

/** Живой зал: реальные участники мероприятия, знакомство по взаимному согласию и маячок. */
export function LivePanel({ hall, joined, t, intros, busy, onJoin, onMeet, onOpenBeacon }: Props) {
  const introFor = (id: string) => intros.find((i) => i.other.id === id && i.status !== "declined");
  const people = hall?.people ?? [];
  const best = people.filter((p) => p.match);
  const others = people.filter((p) => !p.match);
  const list = (items: LivePerson[]) => (
    <ul className="live-list">
      {items.map((p) => (
        <Person key={p.candidate.id} person={p} t={t} intro={introFor(p.candidate.id)} busy={busy}
                onMeet={() => onMeet(p.candidate.id)} onOpenBeacon={onOpenBeacon} />
      ))}
    </ul>
  );
  return (
    <section className="live">
      <header className="live__head">
        <span className="live__pulse" aria-hidden />
        <div>
          <h2>{t.liveTitle} · {format(t.liveCount, { n: hall?.count ?? 0 })}</h2>
          <p>{t.liveHint}</p>
        </div>
      </header>
      {!joined ? (
        <div className="live__join">
          <button type="button" className="primary-button" onClick={onJoin} disabled={busy}>
            <LogIn size={18} aria-hidden /> {t.liveJoin}
          </button>
          <p>{t.liveJoinHint}</p>
        </div>
      ) : (
        <>
          <p className="notice"><Check size={15} aria-hidden /> {t.liveYou}</p>
          {people.length === 0 && <p className="live__empty"><UsersRound size={18} aria-hidden /> {t.liveEmpty}</p>}
          {best.length > 0 && <><h3 className="live__group">{t.liveBest}</h3>{list(best)}</>}
          {others.length > 0 && <><h3 className="live__group">{t.liveOthers}</h3>{list(others)}</>}
        </>
      )}
    </section>
  );
}
