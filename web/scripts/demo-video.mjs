// Демо-видео: настоящий проход по интерфейсу в Chrome + озвучка синтезом речи macOS.
//
//   KOPIR_URL=http://localhost:8000 OUT=./demo node scripts/demo-video.mjs
//
// Каждая сцена: озвучка `say` → действия в браузере → ожидание, пока не договорит.
// Начало сцены запоминается, затем ffmpeg кладёт озвучку на видео по этим отметкам.

import { execFileSync } from "node:child_process";
import { mkdir, rename } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "playwright-core";

const BASE = process.env.KOPIR_URL ?? "http://localhost:8000";
const OUT = process.env.OUT ?? "demo";
const SIZE = { width: 1280, height: 720 };
const VOICE = "Milena";
const RATE = "190";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function speak(i, text) {
  const file = join(OUT, `voice-${i}.aiff`);
  execFileSync("say", ["-v", VOICE, "-r", RATE, "-o", file, text]);
  const info = execFileSync("afinfo", [file]).toString();
  return { file, seconds: Number(/estimated duration: ([\d.]+)/.exec(info)[1]) };
}

// Видимый курсор и «волна» при клике: в записи Playwright курсора нет.
const CURSOR = () => {
  const add = () => {
    const dot = document.createElement("div");
    dot.style.cssText = "position:fixed;z-index:99999;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;"
      + "background:rgb(255 255 255 / 85%);border:2px solid #0b93b3;box-shadow:0 2px 8px rgb(0 0 0 / 30%);pointer-events:none;"
      + "transition:transform .12s;left:-50px;top:-50px";
    document.body.appendChild(dot);
    addEventListener("mousemove", (e) => { dot.style.left = `${e.clientX}px`; dot.style.top = `${e.clientY}px`; }, true);
    addEventListener("mousedown", () => { dot.style.transform = "scale(.7)"; }, true);
    addEventListener("mouseup", () => { dot.style.transform = ""; }, true);
  };
  if (document.body) add(); else addEventListener("DOMContentLoaded", add);
};

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome" });
  const context = await browser.newContext({ viewport: SIZE, recordVideo: { dir: OUT, size: SIZE } });
  await context.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("kopir.theme", JSON.stringify("light"));
    localStorage.setItem("kopir.lang", JSON.stringify("ru"));
  });
  await context.addInitScript(CURSOR);
  const page = await context.newPage();
  const started = Date.now();
  let mouse = { x: 640, y: 360 };

  const moveTo = async (locator) => {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    const target = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
    await page.mouse.move(target.x, target.y, { steps: 18 });
    mouse = target;
    await sleep(150);
  };
  const click = async (locator) => {
    await moveTo(locator);
    await page.mouse.down();
    await sleep(80);
    await page.mouse.up();
    await sleep(250);
  };
  const scrollBy = async (dy, ms = 1200) => {
    const steps = Math.max(1, Math.round(ms / 40));
    for (let i = 0; i < steps; i++) {
      await page.mouse.wheel(0, dy / steps);
      await sleep(40);
    }
  };

  const tracks = [];
  const scene = async (text, actions) => {
    const voice = speak(tracks.length, text);
    const at = (Date.now() - started) / 1000;
    tracks.push({ ...voice, at });
    const t0 = Date.now();
    await actions();
    const left = voice.seconds * 1000 + 500 - (Date.now() - t0);
    if (left > 0) await sleep(left);
  };

  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.mouse.move(mouse.x, mouse.y);

  await scene("Кёпир — умный нетворкинг для IT-мероприятий. Он знакомит людей, которым знакомство выгодно обоим.", async () => {
    await sleep(1500);
    await moveTo(page.locator(".goal").nth(0));
  });

  await scene("Участник выбирает цель и заполняет короткую анкету: роль, стек, опыт. Можно просто рассказать о себе голосом — поля заполнятся сами.", async () => {
    await click(page.locator(".goal").nth(0));
    await sleep(500);
    await moveTo(page.locator(".voice button"));
    await sleep(1200);
    await click(page.locator(".section__actions > .ghost-button"));
    await sleep(600);
    await scrollBy(700, 2500);
  });

  await scene("Меньше чем за секунду — пять человек, которым он тоже нужен. Объяснение с двух сторон: чем человек полезен вам и чем вы полезны ему. И готовая первая фраза.", async () => {
    await click(page.locator(".primary-button"));
    await page.locator(".result:not(.result--skeleton)").first().waitFor();
    await sleep(1500);
    await moveTo(page.locator(".result").first().locator("h3"));
    await sleep(800);
    await scrollBy(420, 2500);
    await moveTo(page.locator(".result").first().locator(".icon-button"));
  });

  await scene("Хочу познакомиться: контакты откроются, только когда согласны оба. А маячок помогает найти друг друга в толпе — зона, цвет и крупный код на весь экран.", async () => {
    await click(page.locator(".result").first().locator(".meet__button"));
    await page.locator(".beacon").waitFor();
    await sleep(5500);
    await page.keyboard.press("Escape");
  });

  await scene("Не подошло? Укажите причину — личные веса меняются, и подборка сразу пересчитывается.", async () => {
    const second = page.locator(".result").nth(1);
    await click(second.locator(".feedback__button").nth(1));
    await sleep(500);
    await click(second.locator(".feedback .chip").nth(1));
    await page.locator(".notice").waitFor();
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await sleep(800);
    await moveTo(page.locator(".notice"));
  });

  await scene("Интерфейс, объяснения и первая фраза — на казахском, русском и английском.", async () => {
    const lang = page.locator(".topbar .segmented").nth(1).locator("button");
    await click(lang.nth(1));
    await sleep(2200);
    await click(lang.nth(2));
    await sleep(2000);
    await click(lang.nth(0));
  });

  await scene("Кофаундерам Кёпир собирает мини-команду, где каждый полезен каждому. А менторам — круг из нескольких менти с общей темой.", async () => {
    await click(page.locator(".ghost-button--back"));
    await sleep(400);
    await page.evaluate(() => window.scrollTo({ top: 0 }));
    await click(page.locator(".goal").nth(4));
    await click(page.locator(".section__actions > .ghost-button"));
    await page.locator(".primary-button").scrollIntoViewIfNeeded();
    await click(page.locator(".primary-button"));
    await page.locator(".squad").waitFor();
    await sleep(1200);
    await click(page.locator(".squad .meet__button"));
  });

  await scene("Организатор видит зал целиком: карту рынков и связей, дефицит ролей и навыков, выводы и расписание встреч один на один, которое покрывает почти всех участников.", async () => {
    await click(page.locator(".topbar .segmented").first().locator("button").nth(1));
    await page.locator(".map svg").waitFor();
    await sleep(1500);
    await scrollBy(560, 2000);
    const points = page.locator(".map__point circle:nth-child(2)");
    for (const i of [40, 120, 200]) {
      await moveTo(points.nth(i));
      await sleep(900);
    }
    await page.locator(".schedule").scrollIntoViewIfNeeded();
    await sleep(600);
    const slots = page.locator(".schedule .segmented button");
    await click(slots.nth(1));
    await sleep(900);
    await click(slots.nth(2));
  });

  await scene("На контрольном наборе Кёпир работает на потолке данных: семьдесят три процента против четырёх у подхода «похожие люди». Ответ за пять миллисекунд. Кёпир — знакомства, выгодные обоим.", async () => {
    await page.goto(`${BASE}/?view=organizer`);
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
      body{margin:0;height:100vh;display:grid;place-items:center;font-family:-apple-system,"Inter",sans-serif;color:#0e1a23;
        background:radial-gradient(ellipse at 20% 0%,rgb(20 184 207/18%),transparent 60%),#f6f8fa}
      h1{font-size:64px;margin:0 0 8px;letter-spacing:-.03em} p{margin:0 0 36px;color:#4b5966;font-size:22px}
      .grid{display:grid;grid-template-columns:repeat(3,220px);gap:18px}
      .k{background:#fff;border:1px solid #e3e8ed;border-radius:18px;padding:22px}
      .v{font-size:44px;font-weight:800;color:#08708a} .l{color:#4b5966;font-size:15px;margin-top:6px}
      .u{margin-top:32px;color:#7f8c98;font-size:16px}</style></head><body><div style="text-align:center">
      <h1>Kópir</h1><p>Знакомства на IT-мероприятиях, выгодные обоим</p>
      <div class="grid"><div class="k"><div class="v">73%</div><div class="l">≥3 из 5 подходят<br>(потолок данных)</div></div>
      <div class="k"><div class="v">4%</div><div class="l">у «похожих людей»<br>75% невзаимных</div></div>
      <div class="k"><div class="v">5 мс</div><div class="l">ответ API<br>(лимит ТЗ — 3 с)</div></div></div>
      <div class="u">kopir.onrender.com · @KopirAgent · github.com/Nurdaulet-AI/Kopir</div></div></body></html>`);
    await sleep(1000);
  });

  await sleep(800);
  const video = page.video();
  await context.close();
  await browser.close();
  const raw = await video.path();
  await rename(raw, join(OUT, "screen.webm"));

  // Озвучка по отметкам сцен поверх записи экрана.
  const inputs = tracks.flatMap((t) => ["-i", t.file]);
  const delays = tracks.map((t, i) => `[${i + 1}:a]adelay=${Math.round(t.at * 1000)}|${Math.round(t.at * 1000)}[a${i}]`);
  const mix = `${delays.join(";")};${tracks.map((_, i) => `[a${i}]`).join("")}amix=inputs=${tracks.length}:normalize=0[aout]`;
  execFileSync("ffmpeg", [
    "-y", "-i", join(OUT, "screen.webm"), ...inputs, "-filter_complex", mix,
    "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", join(OUT, "kopir-demo.mp4"),
  ], { stdio: "inherit" });
  const total = (Date.now() - started) / 1000;
  console.log(`готово: ${join(OUT, "kopir-demo.mp4")} · ${total.toFixed(1)} с · сцен: ${tracks.length}`);
}

await main();
