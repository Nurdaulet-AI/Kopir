import { Building2, Info, LoaderCircle, Sparkles, TriangleAlert, Users, type LucideIcon } from "lucide-react";
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

/** Карта зала: цвет — рынок, форма — сторона (залитая — ищет, контур — предлагает). */
function HallMap({ points, t }: { points: Point[]; t: Strings }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const W = 1000;
  const H = 520;
  const counts = (market: Market) => points.filter((p) => p.market === market).length;
  const marketLabel: Record<Market, string> = { jobs: t.marketJobs, mentoring: t.marketMentoring, startups: t.marketStartups };
  // Контуры рисуем первыми, залитые — поверх: мелкие кольца не теряются под точками.
  const ordered = [...points].sort((a, b) => (a.side === b.side ? 0 : a.side === "offers" ? -1 : 1));
  return (
    <div className="viz" onMouseLeave={() => { setTip(null); setHovered(null); }}>
      <Legend items={[
        ...MARKETS.map((m) => ({ label: `${marketLabel[m]} · ${counts(m)}`, color: MARKET_COLOR[m] })),
        { label: t.sideSeeks, color: "var(--text-3)" },
        { label: t.sideOffers, color: "var(--text-3)", hollow: true },
      ]} />
      <div className="map">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t.mapTitle} preserveAspectRatio="xMidYMid meet">
          {ordered.map((p) => {
            const cx = p.x * W;
            const cy = (1 - p.y) * H;
            const color = MARKET_COLOR[p.market];
            const hollow = p.side === "offers";
            return (
              <g key={p.id} className={hovered && hovered !== p.id ? "map__point is-dim" : "map__point"}>
                <circle cx={cx} cy={cy} r={hollow ? 5.5 : 6.5} fill={hollow ? "var(--surface)" : color}
                        stroke={hollow ? color : "var(--surface)"} strokeWidth={hollow ? 2.6 : 2} />
                <circle
                  cx={cx} cy={cy} r={14} fill="transparent"
                  onMouseEnter={(e) => {
                    const box = e.currentTarget.ownerSVGElement!.parentElement!.getBoundingClientRect();
                    setHovered(p.id);
                    setTip({
                      x: e.clientX - box.left + 14,
                      y: e.clientY - box.top + 10,
                      content: (<><strong>{p.name}</strong><span>{p.role}</span><span>{p.goal_label}</span></>),
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
          <HallMap points={data.points} t={t} />
        </Panel>
        <Panel title={t.rolesTitle} hint={t.rolesHint}>
          <PairedBars supplyLabel={t.rolesSeekers} demandLabel={t.rolesOpenings}
                      rows={data.roles.map((r) => ({ key: r.role, label: r.label, supply: r.seekers, demand: r.openings }))} />
        </Panel>
        <Panel title={t.skillsTitle} hint={t.skillsHint}>
          <PairedBars supplyLabel={t.skillsSupply} demandLabel={t.skillsDemand}
                      rows={data.skills.map((s) => ({ key: s.skill, label: s.skill, supply: s.supply, demand: s.demand }))} />
        </Panel>
        <Panel title={t.domainsTitle} wide>
          <DomainBars domains={data.domains} />
        </Panel>
      </div>
    </div>
  );
}
