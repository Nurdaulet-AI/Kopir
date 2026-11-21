import { MapPin, Send, Shirt, X } from "lucide-react";
import { useEffect } from "react";
import type { IntroView } from "../api";
import { format, type Strings } from "../i18n";
import { beaconInk } from "./ink";

/** Маячок встречи на весь экран: зона (где), цвет и крупный код (кто), приметы и контакт. */
export function Beacon({ intro, t, onClose }: { intro: IntroView; t: Strings; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    navigator.vibrate?.([120, 80, 120]);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!intro.beacon) return null;
  const { color, code, zone } = intro.beacon;
  const telegram = intro.contact?.telegram;
  return (
    <div className="beacon" style={{ ["--beacon" as string]: color, ["--beacon-ink" as string]: beaconInk(color) }} role="dialog" aria-modal aria-label={t.openBeacon}>
      <button type="button" className="beacon__close" onClick={onClose} aria-label={t.close}>
        <X size={22} aria-hidden />
      </button>
      <p className="beacon__zone"><MapPin size={20} aria-hidden /> {format(t.zone, { n: zone })}</p>
      <p className="beacon__code">{code}</p>
      <p className="beacon__name">{intro.other.name}</p>
      <p className="beacon__hint">{t.beaconHint}</p>
      <div className="beacon__facts">
        {intro.contact?.looks_like && (
          <span><Shirt size={16} aria-hidden /> {t.howToFind}: {intro.contact.looks_like}</span>
        )}
        {telegram && (
          <a href={`https://t.me/${telegram.replace(/^@/, "")}`} target="_blank" rel="noreferrer">
            <Send size={16} aria-hidden /> {telegram}
          </a>
        )}
      </div>
    </div>
  );
}
