import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { LANGS, type Lang } from "../api";
import type { Strings } from "../i18n";

export type Theme = "light" | "dark" | "system";

const LANG_NAMES: Record<Lang, string> = { ru: "RU", kk: "ҚАЗ", en: "EN" };

export function LangSwitch({ value, onChange }: { value: Lang; onChange: (lang: Lang) => void }) {
  return (
    <div className="segmented" role="group" aria-label="Language">
      {LANGS.map((lang) => (
        <button type="button" key={lang} aria-pressed={value === lang} onClick={() => onChange(lang)}>
          {LANG_NAMES[lang]}
        </button>
      ))}
    </div>
  );
}

export function ThemeSwitch({ value, onChange, t }: { value: Theme; onChange: (theme: Theme) => void; t: Strings }) {
  const themes: [Theme, LucideIcon, string][] = [
    ["light", Sun, t.themeLight],
    ["dark", Moon, t.themeDark],
    ["system", Monitor, t.themeSystem],
  ];
  return (
    <div className="segmented segmented--icons" role="group" aria-label={t.themeSystem}>
      {themes.map(([theme, Icon, label]) => (
        <button type="button" key={theme} aria-pressed={value === theme} onClick={() => onChange(theme)}
                title={label} aria-label={label}>
          <Icon size={16} strokeWidth={2} aria-hidden />
        </button>
      ))}
    </div>
  );
}
