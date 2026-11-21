import type { Option } from "../api";

interface Props {
  options: Option[];
  value: string[];
  onChange: (next: string[]) => void;
  labelledBy: string;
  single?: boolean;
}

/** Выбор из коротких вариантов кнопками-чипами: быстрее выпадающего списка на телефоне. */
export function ChipSelect({ options, value, onChange, labelledBy, single = false }: Props) {
  const toggle = (v: string) => {
    if (single) onChange([v]);
    else onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  };
  return (
    <div className="chips" role="group" aria-labelledby={labelledBy}>
      {options.map((o) => (
        <button
          type="button"
          key={o.value}
          className="chip"
          aria-pressed={value.includes(o.value)}
          onClick={() => toggle(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
