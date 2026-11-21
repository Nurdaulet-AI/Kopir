import { Check, Clock, GraduationCap, UsersRound } from "lucide-react";
import type { CSSProperties } from "react";
import type { IntroView, Squad } from "../api";
import type { Strings } from "../i18n";
import { hue, initials } from "./ink";

interface Props {
  squad: Squad;
  t: Strings;
  intros: IntroView[];
  busy: boolean;
  onInvite: () => void;
}

/** Мини-группа над подборкой: команда, где каждый полезен каждому, или круг ментора. */
export function SquadCard({ squad, t, intros, busy, onInvite }: Props) {
  const circle = squad.kind === "circle";
  const status = (id: string) => intros.find((i) => i.other.id === id && i.status !== "declined")?.status;
  const invited = squad.members.every((m) => status(m.id));
  const common = [...squad.skills, ...squad.domains];
  return (
    <section className="squad">
      <header className="squad__head">
        <span className="squad__icon" aria-hidden>{circle ? <GraduationCap size={20} /> : <UsersRound size={20} />}</span>
        <div>
          <h2>{circle ? t.circleTitle : t.teamTitle}</h2>
          <p>{circle ? t.circleHint : t.teamHint}</p>
        </div>
      </header>
      <ul className="squad__members">
        {squad.members.map((m) => {
          const s = status(m.id);
          return (
            <li key={m.id} style={{ "--hue": hue(m.name) } as CSSProperties}>
              <span className="avatar" aria-hidden>{initials(m.name)}</span>
              <span className="squad__who">
                <b>{m.name}</b>
                <small>{m.role_label} · {m.level_label}{m.goal === "be_mentor" ? ` · ${t.mentorTag}` : ""}</small>
              </span>
              {s === "accepted" && <Check size={16} className="squad__ok" aria-label={t.matched} />}
              {s === "pending" && <Clock size={15} className="squad__wait" aria-label={t.requestSent} />}
            </li>
          );
        })}
      </ul>
      <footer className="squad__foot">
        {common.length > 0 && (
          <span className="squad__common">
            {t.groupCommon}: {common.map((c) => <span className="pill" key={c}>{c}</span>)}
          </span>
        )}
        {invited ? (
          <span className="meet__status meet__status--ok"><Check size={15} aria-hidden /> {t.groupInvited}</span>
        ) : (
          <button type="button" className="meet__button" onClick={onInvite} disabled={busy}>
            <UsersRound size={16} aria-hidden /> {t.inviteAll}
          </button>
        )}
      </footer>
    </section>
  );
}
