import { useId } from "react";

/** Знак Kópir — шаңырақ: купол юрты как сеть связей, золотая точка — общее пространство.
 *  Цвет линий берётся из темы (--accent), поэтому знак сам подстраивается под светлую и тёмную. */
export function ShanyraqMark({ size = 30 }: { size?: number }) {
  const clipId = useId();
  return (
    <svg className="brand__mark" width={size} height={size} viewBox="0 0 48 48" aria-hidden>
      <defs>
        <clipPath id={clipId}>
          <circle cx="24" cy="24" r="18.5" />
        </clipPath>
      </defs>
      <circle cx="24" cy="24" r="19" fill="none" stroke="var(--accent)" strokeWidth="3.6" />
      <g clipPath={`url(#${clipId})`} stroke="var(--accent)" strokeWidth="3.2" strokeLinecap="round">
        <path d="M5 33 L33 5 M15 43 L43 15 M5 15 L33 43 M15 5 L43 33" />
      </g>
      <circle cx="24" cy="24" r="3.6" fill="var(--gold)" />
    </svg>
  );
}
