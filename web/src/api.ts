// Типизированный клиент API. Типы зеркалят backend/kopir/api/schemas.py.

export type Lang = "ru" | "kk" | "en";
export const LANGS: Lang[] = ["ru", "kk", "en"];

export type Goal =
  | "find_job"
  | "hire"
  | "find_mentor"
  | "be_mentor"
  | "find_cofounder"
  | "share_experience";
export type Level = "intern" | "junior" | "middle" | "senior" | "lead";

export interface Target {
  roles: string[];
  skills: string[];
  level: Level | null;
  domains: string[];
}

export interface ProfileInput {
  name: string;
  lang: Lang;
  city: string;
  role: string;
  level: Level;
  years: number;
  stack: string[];
  interests: string[];
  about: string;
  goal: Goal;
  target: Target;
  openings: Target[];
  company: string | null;
}

export interface Option {
  value: string;
  label: string;
}

export interface Options {
  goals: Option[];
  roles: Option[];
  levels: Option[];
  domains: Option[];
  skills: string[];
}

export interface Candidate {
  id: string;
  name: string;
  goal: Goal;
  goal_label: string;
  role_label: string;
  level_label: string;
  years: number;
  city: string;
  company: string | null;
  about: string;
}

export interface Explanation {
  label_you: string;
  for_me: string;
  label_them: string;
  for_them: string;
  shared: Partial<Record<"stack" | "topics" | "domain", string[]>>;
  warnings: string[];
  icebreaker: string;
}

export interface Recommendation {
  candidate: Candidate;
  score: number;
  weak: boolean;
  explanation: Explanation;
}

export interface RecommendResponse {
  profile_id: string;
  lang: Lang;
  recommendations: Recommendation[];
  /** Личные веса критериев из отзывов «не подошло». */
  factors: Record<string, number>;
  elapsed_ms: number;
}

export type Reason = "level" | "stack" | "domain" | "other";

export type Feedback =
  | { candidate_id: string; verdict: "met" }
  | { candidate_id: string; verdict: "not_fit"; reason: Reason };

export interface RecommendRequest {
  profile: ProfileInput;
  lang?: Lang;
  k?: number;
  exclude?: string[];
  join?: boolean;
  feedback?: Feedback[];
}

export interface IntroView {
  id: string;
  status: "pending" | "accepted" | "declined";
  direction: "outgoing" | "incoming";
  simulated: boolean;
  other: Candidate;
  beacon: { color: string; code: string; zone: number } | null;
  contact: { telegram: string | null; looks_like: string | null } | null;
}

export interface Squad {
  kind: "team" | "circle";
  members: Candidate[];
  cohesion: number;
  skills: string[];
  domains: string[];
}

export interface ParsedProfile {
  role: string | null;
  level: Level | null;
  years: number | null;
  goal: Goal | null;
  stack: string[];
  interests: string[];
}

/** Ошибка API с человекочитаемым текстом (в том числе из ответа 422). */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface ValidationIssue {
  msg: string;
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[]).map((d) => d.msg.replace(/^Value error, /, "")).join("; ");
  }
  return "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, describe((body as { detail?: unknown }).detail));
  }
  return (await response.json()) as T;
}

export const api = {
  options: (lang: Lang) => request<Options>(`/api/options?lang=${lang}`),
  recommend: (body: RecommendRequest) =>
    request<RecommendResponse>("/api/recommend", { method: "POST", body: JSON.stringify(body) }),
  join: (profile: ProfileInput) =>
    request<{ profile_id: string }>("/api/profiles", { method: "POST", body: JSON.stringify({ profile }) }),
  intro: (fromId: string, toId: string, lang: Lang) =>
    request<IntroView>(`/api/intros?lang=${lang}`, { method: "POST", body: JSON.stringify({ from_id: fromId, to_id: toId }) }),
  respond: (introId: string, profileId: string, accept: boolean, lang: Lang) =>
    request<IntroView>(`/api/intros/${introId}/respond?lang=${lang}`, {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, accept }),
    }),
  intros: (profileId: string, lang: Lang) =>
    request<IntroView[]>(`/api/intros?profile_id=${encodeURIComponent(profileId)}&lang=${lang}`),
  squad: (profile: ProfileInput, lang: Lang) =>
    request<Squad | null>("/api/squad", { method: "POST", body: JSON.stringify({ profile, lang }) }),
  parse: (text: string) => request<ParsedProfile>("/api/parse", { method: "POST", body: JSON.stringify({ text }) }),
};
