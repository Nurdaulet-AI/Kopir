import type { CSSProperties, ReactNode } from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";

export const FPS = 30;
const PAD = 1.2;

// Длительности озвучки (edge-tts, ru-RU-SvetlanaNeural) и клипов экрана, секунды.
const VOICE = [7.776, 8.376, 8.208, 13.296, 6.0, 7.272, 4.44, 6.168, 9.84];

interface Chapter {
  n: string;
  title: string;
  subtitle: string;
  clip: string;
  clipSec: number;
  wide?: boolean;
}

const CHAPTERS: Chapter[] = [
  { n: "01", title: "Анкета за минуту", subtitle: "Цель, роль, стек, опыт — или просто расскажите голосом", clip: "c1-form", clipSec: 8.96 },
  { n: "02", title: "5 нужных людей за 5 мс", subtitle: "Каждому из них вы тоже нужны. Объяснение с двух сторон и первая фраза", clip: "c2-results", clipSec: 13.08 },
  { n: "03", title: "Двойное согласие и маячок", subtitle: "Контакты — только когда «да» сказали оба. Время встречи и зона — автоматически", clip: "c3-meet", clipSec: 14.36 },
  { n: "04", title: "Обратная связь", subtitle: "«Не подошло» — и подборка сразу пересчитывается", clip: "c4-feedback", clipSec: 7.44 },
  { n: "05", title: "Мини-команды", subtitle: "Каждый полезен каждому. Один маячок и одно время на всю группу", clip: "c5-squad", clipSec: 13.6 },
  { n: "06", title: "Қазақша · Русский · English", subtitle: "Веб и Telegram Mini App", clip: "c6-lang", clipSec: 9.12 },
  { n: "07", title: "Дашборд организатора", subtitle: "Карта связей зала, дефицит ролей, расписание встреч 1:1", clip: "c7-dashboard", clipSec: 10.6, wide: true },
];

const sec = (i: number) => Math.round((VOICE[i] + PAD) * FPS);
const INTRO = sec(0);
const OUTRO = Math.round((VOICE[8] + 1.8) * FPS);
const CH = CHAPTERS.map((_, i) => sec(i + 1));
export const totalFrames = INTRO + CH.reduce((a, b) => a + b, 0) + OUTRO;

const FONT = '"Inter", -apple-system, "SF Pro Display", "Segoe UI", sans-serif';
const TEAL = "#2cc5dd";

function Background() {
  const f = useCurrentFrame();
  const drift = Math.sin(f / 90) * 60;
  const stars = Array.from({ length: 70 }, (_, i) => {
    const x = (i * 977) % 1920;
    const y = (i * 563) % 1080;
    const tw = 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(f / 18 + i));
    return <div key={i} style={{ position: "absolute", left: x, top: y, width: 3, height: 3, borderRadius: 3, background: "#cfefff", opacity: tw }} />;
  });
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(1100px 700px at ${1450 + drift}px 380px, rgba(20,184,207,.28), transparent 60%),
        radial-gradient(900px 700px at ${200 - drift}px 1000px, rgba(57,135,229,.25), transparent 60%), #050a14`,
    }}>
      {stars}
    </AbsoluteFill>
  );
}

function Logo() {
  return (
    <div style={{ position: "absolute", left: 80, top: 64, display: "flex", alignItems: "center", gap: 16 }}>
      <Img src={staticFile("logo.svg")} style={{ width: 52, height: 52 }} />
      <span style={{ fontFamily: FONT, fontWeight: 800, fontSize: 36, color: "#fff", letterSpacing: -0.5 }}>Kópir</span>
    </div>
  );
}

function useIn(delay = 0) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping: 18, mass: 0.8 } });
}

function Rise({ delay = 0, children, style }: { delay?: number; children: ReactNode; style?: CSSProperties }) {
  const p = useIn(delay);
  return <div style={{ ...style, opacity: p, transform: `translateY(${(1 - p) * 40}px)` }}>{children}</div>;
}

function Fade({ frames, children }: { frames: number; children: ReactNode }) {
  const f = useCurrentFrame();
  const out = interpolate(f, [frames - 10, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: out }}>{children}</AbsoluteFill>;
}

function Device({ chapter, frames }: { chapter: Chapter; frames: number }) {
  const p = useIn(4);
  const f = useCurrentFrame();
  const rate = Math.min(2.2, Math.max(0.75, chapter.clipSec / (frames / FPS)));
  const float = Math.sin(f / 40) * 6;
  const video = <OffthreadVideo src={staticFile(`clips/${chapter.clip}.mp4`)} playbackRate={rate} muted
                                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />;
  if (chapter.wide) {
    return (
      <div style={{
        position: "absolute", right: 70, top: 200, width: 1040, height: 690, borderRadius: 22, overflow: "hidden",
        background: "#0b1220", border: "1px solid rgba(255,255,255,.12)", boxShadow: "0 40px 120px rgba(0,0,0,.6), 0 0 80px rgba(44,197,221,.18)",
        transform: `perspective(1600px) translateX(${(1 - p) * 300}px) translateY(${float}px) rotateY(${(1 - p) * -18 - 4}deg)`, opacity: p,
      }}>
        <div style={{ height: 40, background: "#111a26", display: "flex", alignItems: "center", gap: 8, paddingLeft: 16 }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 12, height: 12, borderRadius: 12, background: c }} />)}
          <span style={{ marginLeft: 20, fontFamily: FONT, fontSize: 15, color: "#6c7a87" }}>kopir.onrender.com/?view=organizer</span>
        </div>
        <div style={{ height: 650 }}>{video}</div>
      </div>
    );
  }
  return (
    <div style={{
      position: "absolute", right: 250, top: 70, width: 430, height: 930, borderRadius: 64, padding: 16, background: "#0d1117",
      border: "2px solid #2a3442", boxShadow: "0 50px 120px rgba(0,0,0,.65), 0 0 90px rgba(44,197,221,.22)",
      transform: `perspective(1600px) translateX(${(1 - p) * 260}px) translateY(${float}px) rotateY(${(1 - p) * -25 - 6}deg)`, opacity: p,
    }}>
      <div style={{ width: "100%", height: "100%", borderRadius: 50, overflow: "hidden", position: "relative", background: "#fff" }}>
        {video}
        <div style={{ position: "absolute", top: 10, left: "50%", marginLeft: -60, width: 120, height: 32, borderRadius: 20, background: "#0d1117" }} />
      </div>
    </div>
  );
}

function ChapterScene({ chapter, index, frames }: { chapter: Chapter; index: number; frames: number }) {
  const f = useCurrentFrame();
  const progress = interpolate(f, [0, frames], [0, 1], { extrapolateRight: "clamp" });
  return (
    <Fade frames={frames}>
      <Logo />
      <div style={{ position: "absolute", left: 80, top: chapter.wide ? 330 : 380, width: chapter.wide ? 640 : 1080, fontFamily: FONT }}>
        <Rise>
          <span style={{
            display: "inline-block", padding: "8px 20px", borderRadius: 999, fontSize: 26, fontWeight: 800, color: "#04121a",
            background: `linear-gradient(135deg, #5be3f2, ${TEAL})`,
          }}>{chapter.n}</span>
        </Rise>
        <Rise delay={5} style={{ marginTop: 26 }}>
          <div style={{ fontSize: chapter.wide ? 64 : 76, fontWeight: 800, color: "#fff", lineHeight: 1.05, letterSpacing: -1.5 }}>{chapter.title}</div>
        </Rise>
        <Rise delay={10} style={{ marginTop: 22 }}>
          <div style={{ fontSize: 32, color: "#a3b0bc", lineHeight: 1.35 }}>{chapter.subtitle}</div>
        </Rise>
      </div>
      <Device chapter={chapter} frames={frames} />
      <div style={{ position: "absolute", left: 80, bottom: 70, width: 420, height: 4, borderRadius: 4, background: "rgba(255,255,255,.1)" }}>
        <div style={{ width: `${((index + progress) / CHAPTERS.length) * 100}%`, height: "100%", borderRadius: 4, background: TEAL }} />
      </div>
    </Fade>
  );
}

function Intro() {
  const p = useIn(0);
  return (
    <Fade frames={INTRO}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, textAlign: "center" }}>
        <Img src={staticFile("logo.svg")} style={{ width: 170, height: 170, transform: `scale(${0.6 + 0.4 * p}) rotate(${(1 - p) * -90}deg)`, opacity: p }} />
        <Rise delay={8} style={{ marginTop: 26 }}>
          <div style={{ fontSize: 150, fontWeight: 800, color: "#fff", letterSpacing: -4, lineHeight: 1 }}>Kópir</div>
        </Rise>
        <Rise delay={16} style={{ marginTop: 18 }}>
          <div style={{ fontSize: 44, color: "#cfe9f0", fontWeight: 600 }}>Знакомства на IT-мероприятиях, выгодные обоим</div>
        </Rise>
        <Rise delay={26} style={{ marginTop: 34 }}>
          <span style={{ padding: "10px 24px", borderRadius: 999, fontSize: 24, fontWeight: 700, color: TEAL, border: `2px solid ${TEAL}` }}>
            Qazaq IT Community · AIHack 2026
          </span>
        </Rise>
      </AbsoluteFill>
    </Fade>
  );
}

function Metric({ value, suffix, label, delay }: { value: number; suffix: string; label: string; delay: number }) {
  const f = useCurrentFrame();
  const p = useIn(delay);
  const n = Math.round(interpolate(f - delay, [0, 30], [0, value], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <div style={{
      width: 360, padding: "30px 26px", borderRadius: 28, background: "rgba(255,255,255,.06)", border: "1px solid rgba(255,255,255,.12)",
      opacity: p, transform: `translateY(${(1 - p) * 50}px)`,
    }}>
      <div style={{ fontSize: 84, fontWeight: 800, color: TEAL, letterSpacing: -2 }}>{n}{suffix}</div>
      <div style={{ fontSize: 24, color: "#a3b0bc", marginTop: 6, lineHeight: 1.3 }}>{label}</div>
    </div>
  );
}

function Outro() {
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, textAlign: "center" }}>
      <Rise><Img src={staticFile("logo.svg")} style={{ width: 110, height: 110 }} /></Rise>
      <Rise delay={5} style={{ marginTop: 14 }}><div style={{ fontSize: 96, fontWeight: 800, color: "#fff", letterSpacing: -3 }}>Kópir</div></Rise>
      <Rise delay={10}><div style={{ fontSize: 36, color: "#cfe9f0", fontWeight: 600 }}>Знакомства, выгодные обоим</div></Rise>
      <div style={{ display: "flex", gap: 30, marginTop: 56 }}>
        <Metric value={73} suffix="%" label={"≥3 из 5 подходят —\nпотолок данных"} delay={18} />
        <Metric value={4} suffix="%" label={"у «похожих людей»,\n75% невзаимных"} delay={26} />
        <Metric value={5} suffix=" мс" label={"на подбор\n(лимит ТЗ — 3 с)"} delay={34} />
      </div>
      <Rise delay={50} style={{ marginTop: 56 }}>
        <div style={{ fontSize: 28, color: "#6c7a87", fontWeight: 600 }}>kopir.onrender.com · @KopirAgent · github.com/Nurdaulet-AI/Kopir</div>
      </Rise>
    </AbsoluteFill>
  );
}

export function Demo() {
  let at = INTRO;
  return (
    <AbsoluteFill style={{ background: "#050a14" }}>
      <Background />
      <Sequence durationInFrames={INTRO}><Intro /></Sequence>
      <Sequence from={6} durationInFrames={INTRO}><Audio src={staticFile("voice/v0.mp3")} /></Sequence>
      {CHAPTERS.map((c, i) => {
        const from = at;
        at += CH[i];
        return (
          <Sequence key={c.n} from={from} durationInFrames={CH[i]}>
            <ChapterScene chapter={c} index={i} frames={CH[i]} />
            <Sequence from={8}><Audio src={staticFile(`voice/v${i + 1}.mp3`)} /></Sequence>
          </Sequence>
        );
      })}
      <Sequence from={at}><Outro /></Sequence>
      <Sequence from={at + 10}><Audio src={staticFile("voice/v8.mp3")} /></Sequence>
    </AbsoluteFill>
  );
}
