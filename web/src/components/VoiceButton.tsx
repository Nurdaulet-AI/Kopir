import { Mic, MicOff } from "lucide-react";
import { useRef, useState } from "react";
import type { Lang } from "../api";
import type { Strings } from "../i18n";

// Web Speech API: распознавание делает браузер, на сервер уходит только текст.
interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}
type RecognitionCtor = new () => Recognition;

const SPEECH_LANG: Record<Lang, string> = { ru: "ru-RU", kk: "kk-KZ", en: "en-US" };

function recognitionCtor(): RecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Кнопка «Рассказать голосом»: по окончании речи отдаёт распознанный текст. */
export function VoiceButton({ lang, t, onText }: { lang: Lang; t: Strings; onText: (text: string) => void }) {
  const [listening, setListening] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const recognition = useRef<Recognition | null>(null);

  const toggle = () => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const Ctor = recognitionCtor();
    if (!Ctor) {
      setHint(t.voiceUnsupported);
      return;
    }
    const r = new Ctor();
    r.lang = SPEECH_LANG[lang];
    r.interimResults = false;
    r.continuous = true;
    let text = "";
    r.onresult = (e) => {
      text = Array.from(e.results, (res) => res[0].transcript).join(" ");
    };
    r.onerror = () => setListening(false);
    r.onend = () => {
      setListening(false);
      setHint(null);
      if (text.trim()) onText(text.trim());
    };
    recognition.current = r;
    r.start();
    setListening(true);
    setHint(t.voiceListening);
  };

  return (
    <span className="voice">
      <button type="button" className={listening ? "ghost-button is-recording" : "ghost-button"} onClick={toggle}
              aria-pressed={listening}>
        {listening ? <MicOff size={16} aria-hidden /> : <Mic size={16} aria-hidden />} {t.voice}
      </button>
      {hint && <span className="voice__hint" role="status">{hint}</span>}
    </span>
  );
}
