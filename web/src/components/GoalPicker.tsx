import type { Goal, Option } from "../api";

const ICONS: Record<Goal, string> = {
  find_job: "💼",
  hire: "🧲",
  find_mentor: "🧭",
  be_mentor: "🎓",
  find_cofounder: "🚀",
  share_experience: "🔄",
};

interface Props {
  goals: Option[];
  value: Goal | null;
  onChange: (goal: Goal) => void;
  title: string;
}

export function GoalPicker({ goals, value, onChange, title }: Props) {
  return (
    <fieldset className="goals">
      <legend className="section-title">{title}</legend>
      <div className="goals__grid">
        {goals.map((g) => (
          <button
            type="button"
            key={g.value}
            className="goal"
            aria-pressed={value === g.value}
            onClick={() => onChange(g.value as Goal)}
          >
            <span className="goal__icon" aria-hidden>
              {ICONS[g.value as Goal]}
            </span>
            <span>{g.label}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
