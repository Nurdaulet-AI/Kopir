import { BriefcaseBusiness, Check, Compass, GraduationCap, MessagesSquare, Rocket, UserPlus, type LucideIcon } from "lucide-react";
import type { Goal, Option } from "../api";

const ICONS: Record<Goal, LucideIcon> = {
  find_job: BriefcaseBusiness,
  hire: UserPlus,
  find_mentor: Compass,
  be_mentor: GraduationCap,
  find_cofounder: Rocket,
  share_experience: MessagesSquare,
};

interface Props {
  goals: Option[];
  hints: Record<Goal, string>;
  value: Goal | null;
  onChange: (goal: Goal) => void;
  labelledBy: string;
}

export function GoalPicker({ goals, hints, value, onChange, labelledBy }: Props) {
  return (
    <div className="goals" role="group" aria-labelledby={labelledBy}>
      {goals.map((g) => {
        const goal = g.value as Goal;
        const Icon = ICONS[goal];
        return (
          <button type="button" key={goal} className="goal" aria-pressed={value === goal} onClick={() => onChange(goal)}>
            <span className="goal__icon" aria-hidden>
              <Icon size={20} strokeWidth={1.8} />
            </span>
            <span className="goal__title">{g.label}</span>
            <span className="goal__hint">{hints[goal]}</span>
            {value === goal && (
              <span className="goal__check" aria-hidden>
                <Check size={14} strokeWidth={3} />
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
