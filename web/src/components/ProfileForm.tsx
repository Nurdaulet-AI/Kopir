import { ArrowRight, LoaderCircle, Plus, Sparkles, X } from "lucide-react";
import { useId, type FormEvent, type ReactNode } from "react";
import type { Level, Options } from "../api";
import type { Strings } from "../i18n";
import { EMPTY_OPENING, type Draft, type OpeningDraft } from "../profile";
import { ChipSelect } from "./ChipSelect";
import { Field } from "./Field";
import { GoalPicker } from "./GoalPicker";
import { TagInput } from "./TagInput";

interface Props {
  draft: Draft;
  onChange: (patch: Partial<Draft>) => void;
  onExample: () => void;
  onSubmit: () => void;
  options: Options;
  t: Strings;
  busy: boolean;
  error: string | null;
}

function Section({ step, title, action, children }: { step: number; title: string; action?: ReactNode; children: ReactNode }) {
  const titleId = useId();
  return (
    <section className="section" aria-labelledby={titleId}>
      <header className="section__head">
        <span className="section__step" aria-hidden>{step}</span>
        <h2 id={titleId}>{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

export function ProfileForm({ draft, onChange, onExample, onSubmit, options, t, busy, error }: Props) {
  const goalTitleId = useId();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };
  const setOpening = (i: number, patch: Partial<OpeningDraft>) =>
    onChange({ openings: draft.openings.map((o, j) => (j === i ? { ...o, ...patch } : o)) });
  const roleOptions = options.roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>);

  return (
    <form className="form" onSubmit={submit} noValidate>
      <section className="section" aria-labelledby={goalTitleId}>
        <header className="section__head">
          <span className="section__step" aria-hidden>1</span>
          <h2 id={goalTitleId}>{t.goalQuestion}</h2>
        </header>
        <GoalPicker goals={options.goals} hints={t.goalHint} value={draft.goal}
                    onChange={(goal) => onChange({ goal })} labelledBy={goalTitleId} />
      </section>

      {draft.goal && (
        <>
          <Section
            step={2}
            title={t.aboutYou}
            action={
              <button type="button" className="ghost-button" onClick={onExample}>
                <Sparkles size={16} aria-hidden /> {t.fillExample}
              </button>
            }
          >
            <div className="grid">
              <Field label={t.name}>
                {(_, id) => (
                  <input id={id} value={draft.name} placeholder={t.namePlaceholder}
                         onChange={(e) => onChange({ name: e.target.value })} autoComplete="name" />
                )}
              </Field>
              <Field label={t.city}>
                {(_, id) => <input id={id} value={draft.city} onChange={(e) => onChange({ city: e.target.value })} />}
              </Field>
              <Field label={t.role}>
                {(_, id) => (
                  <select id={id} value={draft.role} onChange={(e) => onChange({ role: e.target.value })}>
                    <option value="" disabled>—</option>
                    {roleOptions}
                  </select>
                )}
              </Field>
              <Field label={t.years}>
                {(_, id) => (
                  <input id={id} type="number" min={0} max={50} step={0.5} value={draft.years}
                         onChange={(e) => onChange({ years: Math.max(0, Number(e.target.value) || 0) })} />
                )}
              </Field>
              <Field label={t.level} wide>
                {(labelId) => (
                  <ChipSelect options={options.levels} value={[draft.level]} single variant="segmented"
                              labelledBy={labelId} onChange={([level]) => onChange({ level: level as Level })} />
                )}
              </Field>
              <Field label={t.stack} wide>
                {(labelId) => (
                  <TagInput value={draft.stack} onChange={(stack) => onChange({ stack })}
                            suggestions={options.skills} placeholder={t.skillsPlaceholder} labelledBy={labelId} />
                )}
              </Field>
              <Field label={t.interests} wide>
                {(labelId) => (
                  <ChipSelect options={options.domains} value={draft.interests} labelledBy={labelId}
                              onChange={(interests) => onChange({ interests })} />
                )}
              </Field>
              <Field label={t.about} wide>
                {(_, id) => (
                  <textarea id={id} rows={3} value={draft.about} placeholder={t.aboutPlaceholder}
                            onChange={(e) => onChange({ about: e.target.value })} />
                )}
              </Field>
            </div>
          </Section>

          <Section step={3} title={t.whoYouSeek}>
            <div className="grid">
              {draft.goal === "find_job" && (
                <Field label={t.desiredRole}>
                  {(_, id) => (
                    <select id={id} value={draft.desiredRole || draft.role}
                            onChange={(e) => onChange({ desiredRole: e.target.value })}>
                      <option value="" disabled>—</option>
                      {roleOptions}
                    </select>
                  )}
                </Field>
              )}

              {(draft.goal === "find_mentor" || draft.goal === "be_mentor" || draft.goal === "share_experience") && (
                <Field
                  label={{ find_mentor: t.topicsLearn, be_mentor: t.topicsTeach, share_experience: t.topicsShare }[draft.goal]}
                  wide
                >
                  {(labelId) => (
                    <TagInput value={draft.topics} onChange={(topics) => onChange({ topics })}
                              suggestions={options.skills} placeholder={t.skillsPlaceholder} labelledBy={labelId} />
                  )}
                </Field>
              )}

              {draft.goal === "find_cofounder" && (
                <Field label={t.cofounderRoles} wide>
                  {(labelId) => (
                    <ChipSelect options={options.roles} value={draft.cofounderRoles} labelledBy={labelId}
                                onChange={(cofounderRoles) => onChange({ cofounderRoles })} />
                  )}
                </Field>
              )}

              {draft.goal === "hire" && (
                <>
                  <Field label={t.company}>
                    {(_, id) => (
                      <input id={id} value={draft.company} onChange={(e) => onChange({ company: e.target.value })} />
                    )}
                  </Field>
                  <div className="field field--wide">
                    <span className="field__label">{t.openings}</span>
                    <div className="openings">
                      {draft.openings.map((o, i) => (
                        <div className="opening" key={i}>
                          <select aria-label={t.role} value={o.role} onChange={(e) => setOpening(i, { role: e.target.value })}>
                            <option value="" disabled>{t.role}</option>
                            {roleOptions}
                          </select>
                          <select aria-label={t.level} value={o.level}
                                  onChange={(e) => setOpening(i, { level: e.target.value as Level })}>
                            {options.levels.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                          </select>
                          {draft.openings.length > 1 && (
                            <button type="button" className="icon-button" aria-label={t.remove} title={t.remove}
                                    onClick={() => onChange({ openings: draft.openings.filter((_, j) => j !== i) })}>
                              <X size={16} aria-hidden />
                            </button>
                          )}
                          <TagInput value={o.skills} onChange={(skills) => setOpening(i, { skills })}
                                    suggestions={options.skills} placeholder={t.skillsPlaceholder} label={t.stack} />
                        </div>
                      ))}
                      <button type="button" className="ghost-button ghost-button--dashed"
                              onClick={() => onChange({ openings: [...draft.openings, EMPTY_OPENING] })}>
                        <Plus size={16} aria-hidden /> {t.addOpening}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Section>

          {error && <p className="alert alert--error" role="alert">{error}</p>}
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? <LoaderCircle size={18} className="spin" aria-hidden /> : null}
            {busy ? t.searching : t.submit}
            {!busy && <ArrowRight size={18} aria-hidden />}
          </button>
        </>
      )}
    </form>
  );
}
