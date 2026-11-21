import { LANGS, type Lang } from "../api";

const NAMES: Record<Lang, string> = { ru: "RU", kk: "ҚАЗ", en: "EN" };

export function LangSwitch({ value, onChange }: { value: Lang; onChange: (lang: Lang) => void }) {
  return (
    <div className="lang" role="group" aria-label="Language">
      {LANGS.map((lang) => (
        <button type="button" key={lang} aria-pressed={value === lang} onClick={() => onChange(lang)}>
          {NAMES[lang]}
        </button>
      ))}
    </div>
  );
}
