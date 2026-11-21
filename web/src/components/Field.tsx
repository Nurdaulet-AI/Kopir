import { useId, type ReactNode } from "react";

interface Props {
  label: string;
  children: (labelId: string, inputId: string) => ReactNode;
  wide?: boolean;
}

/** Подпись и поле, связанные id: и для `<label for>`, и для групп через aria-labelledby. */
export function Field({ label, children, wide = false }: Props) {
  const labelId = useId();
  const inputId = useId();
  return (
    <div className={wide ? "field field--wide" : "field"}>
      <label className="field__label" id={labelId} htmlFor={inputId}>
        {label}
      </label>
      {children(labelId, inputId)}
    </div>
  );
}
