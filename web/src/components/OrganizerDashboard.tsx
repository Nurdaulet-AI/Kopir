import { ArrowLeftRight, Building2, Info, LoaderCircle, MapPin, Sparkles, TriangleAlert, Users, type LucideIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { ApiError, type Lang } from "../api";
import { format, type Strings } from "../i18n";

// --- данные ---

interface Point {
  id: string;
  name: string;
  role: string;
  goal_label: string;
  market: Market;
  side: "seeks" | "offers";
  x: number;
  y: number;
}
type Market = "jobs" | "mentoring" | "startups";

interface Dashboard {
  participants: number;
  hirers: number;
  openings: number;
  well_matched: number;
  roles: { role: string; label: string; seekers: number; openings: number }[];
  skills: { skill: string; demand: number; supply: number }[];
  domains: { domain: string; label: string; count: number }[];
  points: Point[];
  insights: { kind: string; text: string }[];
  slots: Slot[];
  scheduled: number;
}

interface Meeting {
  a_id: string;
  b_id: string;
  a: string;
  a_role: string;
  b: string;
  b_role: string;
  score: number;
  zone: number;
}
interface Slot {
  time: string;
  meetings: Meeting[];
}

async function loadDashboard(lang: Lang): Promise<Dashboard> {
  const response = await fetch(`/api/dashboard?lang=${lang}`);
  if (!response.ok) throw new ApiError(response.status, "");
  return (await response.json()) as Dashboard;
}

// Цвета рынков: первые три слота проверенной категориальной палитры (валидатор: все пары).
const MARKETS: Market[] = ["jobs", "mentoring", "startups"];
const MARKET_COLOR: Record<Market, string> = {
  jobs: "var(--series-1)",
  mentoring: "var(--series-2)",
  startups: "var(--series-3)",
};

// --- подсказка при наведении ---

interface Tip {
  x: number;
  y: number;
  content: ReactNode;
}

function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  return (
    <div className="viz-tip" style={{ left: tip.x, top: tip.y }} role="status">
      {tip.content}
    </div>
  );
}

// --- части дашборда ---

function Kpi({ icon: Icon, value, label, hint }: { icon: LucideIcon; value: string; label: string; hint?: string }) {
  return (
    <div className="kpi">
      <span className="kpi__icon" aria-hidden><Icon size={18} /></span>
      <span className="kpi__value">{value}</span>
      <span className="kpi__label">{label}</span>
      {hint && <span className="kpi__hint">{hint}</span>}
    </div>
  );
}

function Panel({ title, hint, children, wide = false }: { title: string; hint?: string; children: ReactNode; wide?: boolean }) {
  return (
    <section className={wide ? "panel panel--wide" : "panel"}>
      <header className="panel__head">
        <h2>{title}</h2>
        {hint && <p>{hint}</p>}
      </header>
      {children}
    </section>
  );
}

function Legend({ items }: { items: { label: string; color: string; hollow?: boolean }[] }) {
  return (
    <ul className="legend">
      {items.map((item) => (
        <li key={item.label}>
          <span className={item.hollow ? "legend__dot legend__dot--hollow" : "legend__dot"}
                style={{ ["--dot" as string]: item.color }} aria-hidden />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

interface PairRow {
  key: string;
  label: string;
  supply: number;
  demand: number;
}

/** Две тонкие полосы на строку: предложение (синяя) и спрос (оранжевая), одна шкала. */
function PairedBars({ rows, supplyLabel, demandLabel }: { rows: PairRow[]; supplyLabel: string; demandLabel: string }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const max = Math.max(1, ...rows.flatMap((r) => [r.supply, r.demand]));
  return (
    <div className="viz" onMouseLeave={() => setTip(null)}>
      <Legend items={[{ label: supplyLabel, color: "var(--series-1)" }, { label: demandLabel, color: "var(--series-2)" }]} />
      <div className="pairs">
        {rows.map((r) => (
          <div
            className="pairs__row"
            key={r.key}
            onMouseMove={(e) => {
              const box = e.currentTarget.parentElement!.getBoundingClientRect();
              setTip({
                x: e.clientX - box.left + 14,
                y: e.clientY - box.top + 10,
                content: (
                  <>
                    <strong>{r.label}</strong>
                    <span>{supplyLabel}: {r.supply}</span>
                    <span>{demandLabel}: {r.demand}</span>
                  </>
                ),
              });
            }}
          >
            <span className="pairs__label" title={r.label}>{r.label}</span>
            <div className="pairs__bars">
              <div className="bar">
                <span className="bar__fill" style={{ width: `${(r.supply / max) * 100}%`, background: "var(--series-1)" }} />
                <span className="bar__value">{r.supply}</span>
              </div>
              <div className="bar">
                <span className="bar__fill" style={{ width: `${(r.demand / max) * 100}%`, background: "var(--series-2)" }} />
                <span className="bar__value">{r.demand}</span>
              </div>
            </div>
          </div>
        ))}
        <Tooltip tip={tip} />
      </div>
    </div>
  );
}

/** Карта зала — «созвездие»: люди-звёзды, свечение рынков, линии — встречи 1:1 из расписания.
 * Цвет — рынок, форма — сторона (залитая — ищет, контур — предлагает). Наведение подсвечивает пары человека. */
function HallMap({ points, links, t }: { points: Point[]; links: [string, string][]; t: Strings }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const W = 1000;
  const H = 520;
  const pos = new Map(points.map((p) => [p.id, { x: p.x * W, y: (1 - p.y) * H, p }]));
  const marketLabel: Record<Market, string> = { jobs: t.marketJobs, mentoring: t.marketMentoring, startups: t.marketStartups };
  const counts = (market: Market) => points.filter((p) => p.market === market).length;
  // Центр рынка — медиана (среднее тянет к центру зала), радиус свечения — по медианному разбросу.
  const median = (xs: number[]) => {
    const s = [...xs].sort((a, b) => a - b);
    return s.length ? s[Math.floor(s.length / 2)] : 0;
  };
  const clusters = MARKETS.map((m) => {
    const ps = points.filter((p) => p.market === m).map((p) => pos.get(p.id)!);
    const cx = median(ps.map((p) => p.x));
    const cy = median(ps.map((p) => p.y));
    const spread = median(ps.map((p) => Math.hypot(p.x - cx, p.y - cy)));
    return { m, cx, cy, r: Math.max(110, spread * 2.2) };
  });
  const neighbours = new Set(hovered ? links.flatMap(([a, b]) => (a === hovered ? [b] : b === hovered ? [a] : [])) : []);
  const lit = (id: string) => !hovered || id === hovered || neighbours.has(id);
  // Контуры рисуем первыми, залитые — поверх: мелкие кольца не теряются под точками.
  const ordered = [...points].sort((a, b) => (a.side === b.side ? 0 : a.side === "offers" ? -1 : 1));
  return (
    <div className="viz" onMouseLeave={() => { setTip(null); setHovered(null); }}>
      <Legend items={[
        ...MARKETS.map((m) => ({ label: `${marketLabel[m]} · ${counts(m)}`, color: MARKET_COLOR[m] })),
        { label: t.sideSeeks, color: "var(--text-3)" },
        { label: t.sideOffers, color: "var(--text-3)", hollow: true },
      ]} />
      <div className="map map--sky">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.mapTitle} preserveAspectRatio="xMidYMid meet">
          <defs>
            {MARKETS.map((m) => (
              <radialGradient id={`glow-${m}`} key={m}>
                <stop offset="0%" stopColor={MARKET_COLOR[m]} stopOpacity="0.32" />
                <stop offset="60%" stopColor={MARKET_COLOR[m]} stopOpacity="0.08" />
                <stop offset="100%" stopColor={MARKET_COLOR[m]} stopOpacity="0" />
              </radialGradient>
            ))}
          </defs>
          {clusters.map((c) => (
            <circle key={c.m} cx={c.cx} cy={c.cy} r={c.r} fill={`url(#glow-${c.m})`} className="map__glow" />
          ))}
          <g className="map__links">
            {links.map(([a, b]) => {
              const pa = pos.get(a);
              const pb = pos.get(b);
              if (!pa || !pb) return null;
              const active = hovered !== null && (a === hovered || b === hovered);
              return (
                <line key={`${a}-${b}`} x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
                      className={active ? "map__link is-active" : hovered ? "map__link is-dim" : "map__link"} />
              );
            })}
          </g>
          {ordered.map((p) => {
            const { x: cx, y: cy } = pos.get(p.id)!;
            const color = MARKET_COLOR[p.market];
            const hollow = p.side === "offers";
            return (
              <g key={p.id} className={lit(p.id) ? (p.id === hovered ? "map__point is-hot" : "map__point") : "map__point is-dim"}>
                <circle cx={cx} cy={cy} r={hollow ? 5.5 : 6.5} fill={hollow ? "var(--surface)" : color}
                        stroke={hollow ? color : "var(--surface)"} strokeWidth={hollow ? 2.6 : 2} />
                <circle
                  cx={cx} cy={cy} r={14} fill="transparent"
                  onMouseEnter={(e) => {
                    const box = e.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect();
                    const n = links.filter(([a, b]) => a === p.id || b === p.id).length;
                    setHovered(p.id);
                    setTip({
                      x: e.clientX - box.left + 14,
                      y: e.clientY - box.top + 10,
                      content: (<><strong>{p.name}</strong><span>{p.role}</span><span>{p.goal_label}</span>
                        <span>{format(t.scheduleMeetings, { n })}</span></>),
                    });
                  }}
                />
              </g>
            );
          })}
        </svg>
        <Tooltip tip={tip} />
      </div>
      <table className="sr-only">
        <caption>{t.mapTitle}</caption>
        <thead><tr><th>{t.mapTitle}</th><th>{t.sideSeeks}</th><th>{t.sideOffers}</th></tr></thead>
        <tbody>
          {MARKETS.map((m) => (
            <tr key={m}>
              <td>{marketLabel[m]}</td>
              <td>{points.filter((p) => p.market === m && p.side === "seeks").length}</td>
              <td>{points.filter((p) => p.market === m && p.side === "offers").length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Расписание 1:1: вкладки слотов, у каждой пары — зона зала. */
function Schedule({ slots, scheduled, t }: { slots: Slot[]; scheduled: number; t: Strings }) {
  const [active, setActive] = useState(0);
  const slot = slots[active];
  if (!slot) return null;
  return (
    <div className="schedule">
      <div className="schedule__bar">
        <div className="segmented">
          {slots.map((s, i) => (
            <button key={s.time} type="button" aria-pressed={i === active} onClick={() => setActive(i)}>
              {s.time}
            </button>
          ))}
        </div>
        <span className="schedule__meta">
          {format(t.scheduleMeetings, { n: slot.meetings.length })} · {format(t.scheduleCoverage, { n: Math.round(scheduled * 100) })}
        </span>
      </div>
      <ol className="schedule__list">
        {slot.meetings.slice(0, 12).map((m) => (
          <li key={`${m.a_id}-${m.b_id}`} className="schedule__item">
            <span className="schedule__zone"><MapPin size={13} aria-hidden /> {m.zone}</span>
            <span className="schedule__who"><b>{m.a}</b><small>{m.a_role}</small></span>
            <span className="schedule__score" title={`${m.score}%`}><ArrowLeftRight size={14} aria-label={`${m.score}%`} /></span>
            <span className="schedule__who schedule__who--end"><b>{m.b}</b><small>{m.b_role}</small></span>
          </li>
        ))}
      </ol>
      {slot.meetings.length > 12 && <p className="schedule__more">+{slot.meetings.length - 12}</p>}
    </div>
  );
}

function DomainBars({ domains }: { domains: Dashboard["domains"] }) {
  const max = Math.max(1, ...domains.map((d) => d.count));
  return (
    <ul className="domains">
      {domains.map((d) => (
        <li key={d.domain}>
          <span className="domains__label">{d.label}</span>
          <span className="bar">
            <span className="bar__fill" style={{ width: `${(d.count / max) * 100}%`, background: "var(--series-1)" }} />
            <span className="bar__value">{d.count}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

// --- страница ---

export function OrganizerDashboard({ lang, t }: { lang: Lang; t: Strings }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    loadDashboard(lang).then(
      (d) => !cancelled && setData(d),
      () => !cancelled && setFailed(true),
    );
    return () => {
      cancelled = true;
    };
  }, [lang]);

  if (failed) return <p className="alert alert--error" role="alert">{t.errorNetwork}</p>;
  if (!data) return <p className="loading"><LoaderCircle size={18} className="spin" aria-hidden /></p>;

  const topDomain = data.domains[0];
  return (
    <div className="dashboard">
      <section className="dashboard__head">
        <h1>{t.dashTitle}</h1>
        <p>{t.dashSubtitle}</p>
      </section>

      <div className="kpis">
        <Kpi icon={Users} value={String(data.participants)} label={t.kpiParticipants} />
        <Kpi icon={Building2} value={String(data.openings)} label={t.kpiOpenings}
             hint={format(t.kpiCompanies, { n: data.hirers })} />
        <Kpi icon={Sparkles} value={`${Math.round(data.well_matched * 100)}%`} label={t.kpiMatched} hint={t.kpiMatchedHint} />
        {topDomain && <Kpi icon={Info} value={topDomain.label} label={t.kpiTopDomain}
                           hint={format(t.kpiPeople, { n: topDomain.count })} />}
      </div>

      <Panel title={t.insightsTitle} wide>
        <ul className="insights">
          {data.insights.map((i) => {
            const warn = i.kind !== "top_domain";
            return (
              <li key={i.text} className={warn ? "insight insight--warn" : "insight"}>
                <span className="insight__icon" aria-hidden>{warn ? <TriangleAlert size={16} /> : <Info size={16} />}</span>
                <span className="insight__tag">{warn ? t.insightAction : t.insightFact}</span>
                <span>{i.text}</span>
              </li>
            );
          })}
        </ul>
      </Panel>

      <div className="panels">
        <Panel title={t.mapTitle} hint={t.mapHint} wide>
          <HallMap points={data.points} t={t}
                   links={data.slots.flatMap((s) => s.meetings.map((m) => [m.a_id, m.b_id] as [string, string]))} />
        </Panel>
        <Panel title={t.rolesTitle} hint={t.rolesHint}>
          <PairedBars supplyLabel={t.rolesSeekers} demandLabel={t.rolesOpenings}
                      rows={data.roles.map((r) => ({ key: r.role, label: r.label, supply: r.seekers, demand: r.openings }))} />
        </Panel>
        <Panel title={t.skillsTitle} hint={t.skillsHint}>
          <PairedBars supplyLabel={t.skillsSupply} demandLabel={t.skillsDemand}
                      rows={data.skills.map((s) => ({ key: s.skill, label: s.skill, supply: s.supply, demand: s.demand }))} />
        </Panel>
        <Panel title={t.scheduleTitle} hint={t.scheduleHint} wide>
          <Schedule slots={data.slots} scheduled={data.scheduled} t={t} />
        </Panel>
        <Panel title={t.domainsTitle} wide>
          <DomainBars domains={data.domains} />
        </Panel>
      </div>
    </div>
  );
}
