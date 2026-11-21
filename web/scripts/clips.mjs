// Клипы экрана для моушн-видео (video/): по одному на главу, телефон 390×844 и десктоп для дашборда.
//
//   KOPIR_URL=http://localhost:8000 OUT=../video/public/clips node scripts/clips.mjs

import { execFileSync } from "node:child_process";
import { mkdir, readdir, rename, rm } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "playwright-core";

const BASE = process.env.KOPIR_URL ?? "http://localhost:8000";
const OUT = process.env.OUT ?? "clips";
const PHONE = { width: 390, height: 844 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const TOUCH = () => {
  const add = () => {
    const dot = document.createElement("div");
    dot.style.cssText = "position:fixed;z-index:99999;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;"
      + "background:rgb(255 255 255 / 55%);border:2px solid rgb(11 147 179 / 80%);pointer-events:none;opacity:0;"
      + "transition:opacity .2s, transform .15s;left:-60px;top:-60px";
    document.body.appendChild(dot);
    addEventListener("mousemove", (e) => { dot.style.left = `${e.clientX}px`; dot.style.top = `${e.clientY}px`; dot.style.opacity = "1"; }, true);
    addEventListener("mousedown", () => { dot.style.transform = "scale(.75)"; }, true);
    addEventListener("mouseup", () => { dot.style.transform = ""; }, true);
  };
  if (document.body) add(); else addEventListener("DOMContentLoaded", add);
};

async function clip(browser, name, viewport, theme, run) {
  const dir = join(OUT, `tmp-${name}`);
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, recordVideo: { dir, size: viewport } });
  await ctx.addInitScript((t) => {
    localStorage.clear();
    localStorage.setItem("kopir.theme", JSON.stringify(t));
    localStorage.setItem("kopir.lang", JSON.stringify("ru"));
  }, theme);
  await ctx.addInitScript(TOUCH);
  const page = await ctx.newPage();
  const tap = async (locator) => {
    await locator.scrollIntoViewIfNeeded();
    const b = await locator.boundingBox();
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 12 });
    await sleep(120);
    await page.mouse.down();
    await sleep(90);
    await page.mouse.up();
    await sleep(300);
  };
  const scroll = async (dy, ms) => {
    const n = Math.round(ms / 40);
    for (let i = 0; i < n; i++) { await page.mouse.wheel(0, dy / n); await sleep(40); }
  };
  await page.goto(BASE, { waitUntil: "networkidle" });
  await run(page, tap, scroll);
  await ctx.close();
  const [file] = (await readdir(dir)).filter((f) => f.endsWith(".webm"));
  execFileSync("ffmpeg", ["-v", "error", "-y", "-i", join(dir, file), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
    "-an", join(OUT, `${name}.mp4`)]);
  await rm(dir, { recursive: true });
  console.log("клип", name);
}

const results = async (page, tap, goal) => {
  await tap(page.locator(".goal").nth(goal));
  await tap(page.locator(".section__actions > .ghost-button"));
  await tap(page.locator(".primary-button"));
  await page.locator(".result:not(.result--skeleton)").first().waitFor();
};

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
try {
  await clip(browser, "c1-form", PHONE, "light", async (page, tap, scroll) => {
    await sleep(600);
    await tap(page.locator(".goal").nth(0));
    await sleep(400);
    await tap(page.locator(".section__actions > .ghost-button"));
    await sleep(500);
    await scroll(900, 3500);
    await sleep(800);
  });
  await clip(browser, "c2-results", PHONE, "light", async (page, tap, scroll) => {
    await results(page, tap, 0);
    await sleep(1200);
    await scroll(700, 3500);
    await sleep(1200);
    await scroll(500, 2000);
  });
  await clip(browser, "c3-meet", PHONE, "dark", async (page, tap) => {
    await results(page, tap, 0);
    await page.evaluate(() => window.scrollTo({ top: 0 }));
    await sleep(500);
    await tap(page.locator(".result").first().locator(".meet__button"));
    await sleep(1500);
    await page.locator(".beacon").waitFor({ timeout: 15000 });
    await sleep(3500);
    await page.keyboard.press("Escape");
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await sleep(2500);
  });
  await clip(browser, "c4-feedback", PHONE, "light", async (page, tap) => {
    await results(page, tap, 0);
    const first = page.locator(".result").first();
    await tap(first.locator(".feedback__button").nth(1));
    await sleep(400);
    await tap(first.locator(".feedback .chip").nth(1));
    await page.locator(".notice").waitFor();
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await sleep(2500);
  });
  await clip(browser, "c5-squad", PHONE, "dark", async (page, tap) => {
    await results(page, tap, 4);
    await sleep(1200);
    await tap(page.locator(".squad .meet__button"));
    await page.locator(".squad .meet__button--beacon").waitFor({ timeout: 15000 });
    await sleep(800);
    await tap(page.locator(".squad .meet__button--beacon"));
    await sleep(2500);
  });
  await clip(browser, "c6-lang", PHONE, "light", async (page, tap) => {
    await results(page, tap, 1);
    await sleep(800);
    const lang = page.locator(".topbar .segmented").nth(1).locator("button");
    await tap(lang.nth(1));
    await sleep(2000);
    await tap(lang.nth(2));
    await sleep(2000);
  });
  await clip(browser, "c7-dashboard", { width: 1280, height: 800 }, "dark", async (page, tap, scroll) => {
    await page.goto(`${BASE}/?view=organizer`, { waitUntil: "networkidle" });
    await page.locator(".map svg").waitFor();
    await sleep(800);
    await scroll(620, 1800);
    const pts = page.locator(".map__point circle:nth-child(2)");
    for (const i of [40, 150, 230]) {
      const b = await pts.nth(i).boundingBox();
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 14 });
      await sleep(800);
    }
    await page.locator(".schedule").scrollIntoViewIfNeeded();
    await sleep(700);
    await tap(page.locator(".schedule .segmented button").nth(1));
    await sleep(1200);
  });
} finally {
  await browser.close();
}
