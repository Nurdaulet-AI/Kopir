import { useId, useMemo, useState, type KeyboardEvent } from "react";

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
  suggestions: string[];
  placeholder: string;
  /** id видимой подписи; если её нет — `label` как aria-label. */
  labelledBy?: string;
  label?: string;
}

const MAX_SUGGESTIONS = 6;

/** Ввод навыков с автодополнением. Принимает только известные значения из справочника. */
export function TagInput({ value, onChange, suggestions, placeholder, labelledBy, label }: Props) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listId = useId();

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const free = suggestions.filter((s) => !value.includes(s));
    const starts = free.filter((s) => s.toLowerCase().startsWith(q));
    const contains = free.filter((s) => !s.toLowerCase().startsWith(q) && s.toLowerCase().includes(q));
    return [...starts, ...contains].slice(0, MAX_SUGGESTIONS);
  }, [query, suggestions, value]);

  const add = (skill: string) => {
    onChange([...value, skill]);
    setQuery("");
    setActive(0);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && matches.length) {
      e.preventDefault();
      setActive((i) => (i + 1) % matches.length);
    } else if (e.key === "ArrowUp" && matches.length) {
      e.preventDefault();
      setActive((i) => (i - 1 + matches.length) % matches.length);
    } else if ((e.key === "Enter" || e.key === "Tab" || e.key === ",") && matches[active]) {
      e.preventDefault();
      add(matches[active]);
    } else if (e.key === "Backspace" && !query && value.length) {
      onChange(value.slice(0, -1));
    } else if (e.key === "Escape") {
      setQuery("");
    }
  };

  return (
    <div className="tag-input">
      <div className="tag-input__box">
        {value.map((tag) => (
          <span className="tag" key={tag}>
            {tag}
            <button type="button" aria-label={`× ${tag}`} onClick={() => onChange(value.filter((t) => t !== tag))}>
              ×
            </button>
          </span>
        ))}
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          placeholder={value.length ? "" : placeholder}
          aria-labelledby={labelledBy}
          aria-label={labelledBy ? undefined : label}
          role="combobox"
          aria-expanded={matches.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
        />
      </div>
      {matches.length > 0 && (
        <ul className="tag-input__list" id={listId} role="listbox">
          {matches.map((m, i) => (
            <li
              key={m}
              role="option"
              aria-selected={i === active}
              className={i === active ? "is-active" : undefined}
              onMouseDown={(e) => {
                e.preventDefault();
                add(m);
              }}
            >
              {m}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
