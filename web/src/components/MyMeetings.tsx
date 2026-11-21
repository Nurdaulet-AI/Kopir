import { CalendarClock, Clock, Radio } from "lucide-react";
import { useState, type CSSProperties } from "react";
import { api, type IntroView, type Lang, type SlotOption } from "../api";
import { format, type Strings } from "../i18n";
import { beaconInk } from "./ink";

interface Props {
  intros: IntroView[];
  profileId: string;
  lang: Lang;
  t: Strings;
  onOpenBeacon: (intro: IntroView) => void;
  onChanged: () => void;
  onError: (e: unknown) => void;
}

/** Мои встречи 1:1: время, зона, маячок — и запись на другое время, свободное у всех участников. */
export function MyMeetings({ intros, profileId, lang, t, onOpenBeacon, onChanged, onError }: Props) {
  const [picking, setPicking] = useState<string | null>(null);
  const [options, setOptions] = useState<SlotOption[]>([]);
  const [saving, setSaving] = useState(false);

  // Одна строка на маячок: у группы он общий.
  const meetings = Array.from(new Map(intros.filter((i) => i.status === "accepted" && i.beacon)
    .sort((a, b) => a.beacon!.slot - b.beacon!.slot)
    .map((i) => [i.beacon!.code, i])).values());
  if (meetings.length === 0) return null;

  const open = async (intro: IntroView) => {
    if (picking === intro.id) {
      setPicking(null);
      return;
    }
    try {
      setOptions(await api.slots(intro.id, profileId));
      setPicking(intro.id);
    } catch (e) {
      onError(e);
    }
  };

  const pick = async (intro: IntroView, slot: number) => {
    if (slot === intro.beacon!.slot) {
      setPicking(null);
      return;
    }
    setSaving(true);
    try {
      await api.reschedule(intro.id, profileId, slot, lang);
      setPicking(null);
      onChanged();
    } catch (e) {
      onError(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="meetings">
      <h2><CalendarClock size={17} aria-hidden /> {t.myMeetings}</h2>
      <ul>
        {meetings.map((i) => (
          <li key={i.id}>
            <div className="meetings__row">
              <span className="meetings__time">{i.beacon!.time}</span>
              <span className="meetings__who">
                {intros.filter((x) => x.beacon?.code === i.beacon!.code).map((x) => x.other.name).join(", ")}
              </span>
              <button type="button" className="ghost-button meetings__change" onClick={() => void open(i)}
                      aria-expanded={picking === i.id}>
                <Clock size={15} aria-hidden /> {t.changeTime}
              </button>
              <button type="button" className="meet__button meet__button--beacon" onClick={() => onOpenBeacon(i)}
                      style={{ "--beacon": i.beacon!.color, "--beacon-ink": beaconInk(i.beacon!.color) } as CSSProperties}>
                <Radio size={15} aria-hidden /> {format(t.zone, { n: i.beacon!.zone })} · {i.beacon!.code}
              </button>
            </div>
            {picking === i.id && (
              <div className="slots">
                <p className="slots__hint">{t.pickTime}</p>
                <div className="slots__grid">
                  {options.map((o) => (
                    <button key={o.slot} type="button" disabled={!o.free || saving}
                            className={o.slot === i.beacon!.slot ? "slot is-current" : "slot"}
                            aria-pressed={o.slot === i.beacon!.slot} onClick={() => void pick(i, o.slot)}>
                      <b>{o.time}</b>
                      {!o.free && <small>{t.busySlot}</small>}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
