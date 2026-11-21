// Черновик анкеты в форме и его превращение в анкету для API.
// Форма хранит поля всех целей сразу: при смене цели введённое не теряется,
// а в API уходит только то, что относится к выбранной цели.

import type { Goal, Lang, Level, ProfileInput, Target } from "./api";
import type { TextKey } from "./i18n";

export interface OpeningDraft {
  role: string;
  level: Level;
  skills: string[];
}

export interface Draft {
  goal: Goal | null;
  name: string;
  city: string;
  role: string;
  level: Level;
  years: number;
  stack: string[];
  interests: string[];
  about: string;
  desiredRole: string;
  topics: string[];
  cofounderRoles: string[];
  company: string;
  openings: OpeningDraft[];
}

export const EMPTY_OPENING: OpeningDraft = { role: "", level: "middle", skills: [] };

export const EMPTY_DRAFT: Draft = {
  goal: null,
  name: "",
  city: "Алматы",
  role: "",
  level: "junior",
  years: 1,
  stack: [],
  interests: [],
  about: "",
  desiredRole: "",
  topics: [],
  cofounderRoles: [],
  company: "",
  openings: [EMPTY_OPENING],
};

const target = (t: Partial<Target>): Target => ({ roles: [], skills: [], level: null, domains: [], ...t });

export function toProfile(d: Draft, lang: Lang): ProfileInput {
  if (d.goal === null) throw new Error("цель не выбрана");
  const base = {
    name: d.name.trim(),
    lang,
    city: d.city.trim() || "Алматы",
    role: d.role,
    level: d.level,
    years: d.years,
    stack: d.stack,
    interests: d.interests,
    about: d.about.trim(),
    goal: d.goal,
    target: target({}),
    openings: [] as Target[],
    company: null as string | null,
  };
  switch (d.goal) {
    case "find_job":
      return { ...base, target: target({ roles: [d.desiredRole || d.role], domains: d.interests }) };
    case "hire":
      return {
        ...base,
        company: d.company.trim() || null,
        openings: d.openings
          .filter((o) => o.role)
          .map((o) => target({ roles: [o.role], skills: o.skills, level: o.level, domains: d.interests })),
      };
    case "find_mentor":
    case "be_mentor":
      return { ...base, target: target({ skills: d.topics }) };
    case "find_cofounder":
      return { ...base, target: target({ roles: d.cofounderRoles, domains: d.interests }) };
    case "share_experience":
      return { ...base, target: target({ skills: d.topics, domains: d.interests }) };
  }
}

/** Ключ текста ошибки или null, если анкету можно отправлять. */
export function validate(d: Draft): TextKey | null {
  if (!d.name.trim() || !d.role) return "errorRequired";
  if (d.goal === "hire" && !d.openings.some((o) => o.role)) return "errorOpenings";
  return null;
}

type Example = Omit<Partial<Draft>, "goal" | "about"> & { about: Record<Lang, string> };

const EXAMPLES: Record<Goal, Example> = {
  find_job: {
    name: "Аружан Т.", city: "Алматы", role: "backend", level: "junior", years: 1.5,
    stack: ["Python", "FastAPI", "PostgreSQL"], interests: ["fintech"], desiredRole: "backend",
    about: {
      ru: "Junior Python-разработчик, полтора года пишу на FastAPI. Ищу работу в финтехе.",
      kk: "Junior Python-әзірлеушімін, бір жарым жыл FastAPI қолданамын. FinTech саласынан жұмыс іздеймін.",
      en: "Junior Python developer, 1.5 years with FastAPI. Looking for a fintech job.",
    },
  },
  hire: {
    name: "Мадина К.", city: "Алматы", role: "recruiter", level: "senior", years: 6,
    stack: ["Recruiting"], interests: ["ecommerce"], company: "Steppewise",
    openings: [
      { role: "backend", level: "middle", skills: ["Python", "FastAPI", "PostgreSQL"] },
      { role: "frontend", level: "junior", skills: ["React", "TypeScript"] },
    ],
    about: {
      ru: "Рекрутер Steppewise. Ищем Middle Python-бэкендера и Junior React-разработчика.",
      kk: "Steppewise рекрутерімін. Middle Python-әзірлеуші мен Junior React-әзірлеуші іздейміз.",
      en: "Recruiter at Steppewise. Hiring a Middle Python backend and a Junior React developer.",
    },
  },
  find_mentor: {
    name: "Ерлан С.", city: "Астана", role: "frontend", level: "junior", years: 1,
    stack: ["JavaScript", "React"], interests: ["edtech"], topics: ["TypeScript", "Next.js", "System Design"],
    about: {
      ru: "Junior фронтендер. Хочу разобраться в TypeScript и архитектуре, ищу ментора.",
      kk: "Junior frontend-әзірлеушімін. TypeScript пен архитектураны үйренгім келеді, тәлімгер іздеймін.",
      en: "Junior frontend developer. Want to master TypeScript and architecture — looking for a mentor.",
    },
  },
  be_mentor: {
    name: "Дмитрий А.", city: "Алматы", role: "backend", level: "lead", years: 11,
    stack: ["Go", "Kafka", "PostgreSQL", "Kubernetes"], interests: ["fintech"],
    topics: ["Go", "Kafka", "System Design", "Career"],
    about: {
      ru: "Тимлид, 11 лет в бэкенде. Помогу с Go, Kafka и проектированием систем.",
      kk: "Тимлидпін, бэкендте 11 жыл тәжірибем бар. Go, Kafka және жүйе жобалау бойынша көмектесемін.",
      en: "Team lead, 11 years in backend. Happy to help with Go, Kafka and system design.",
    },
  },
  find_cofounder: {
    name: "Әлия Н.", city: "Алматы", role: "business", level: "lead", years: 8,
    stack: ["Sales", "Fundraising"], interests: ["edtech", "ai"], cofounderRoles: ["backend", "fullstack", "ml"],
    about: {
      ru: "Есть идея AI-продукта для школ и опыт привлечения инвестиций. Ищу технического кофаундера.",
      kk: "Мектептерге арналған AI-өнім идеясы және инвестиция тарту тәжірибесі бар. Техникалық тең құрылтайшы іздеймін.",
      en: "I have an AI-for-schools idea and fundraising experience. Looking for a technical co-founder.",
    },
  },
  share_experience: {
    name: "Тимур Б.", city: "Алматы", role: "devops", level: "senior", years: 6,
    stack: ["Kubernetes", "Terraform", "AWS"], interests: ["fintech"], topics: ["Kubernetes", "Terraform"],
    about: {
      ru: "Платформенный инженер в финтехе. Интересно сравнить подходы к Kubernetes в проде.",
      kk: "Финтехтегі платформа инженерімін. Kubernetes бойынша тәжірибе алмасқым келеді.",
      en: "Platform engineer in fintech. Keen to compare notes on Kubernetes in production.",
    },
  },
};

export function example(goal: Goal, lang: Lang): Draft {
  const { about, ...rest } = EXAMPLES[goal];
  return { ...EMPTY_DRAFT, ...rest, goal, about: about[lang] };
}
