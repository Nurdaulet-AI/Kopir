// Скриншоты новых функций: знакомство → маячок, дашборд с расписанием и картой-созвездием.
//
//   KOPIR_URL=http://localhost:8000 OUT=./screenshots node scripts/features.mjs

import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "playwright-core";

const BASE = process.env.KOPIR_URL ?? "http://localhost:8000";
const OUT = process.env.OUT ?? "screenshots";

async function context(browser, theme, viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  await ctx.addInitScript((t) => {
    localStorage.clear();
    localStorage.setItem("kopir.theme", JSON.stringify(t));
    localStorage.setItem("kopir.lang", JSON.stringify("ru"));
  }, theme);
  return ctx;
}

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
try {
  for (const theme of ["light", "dark"]) {
    const ctx = await context(browser, theme, { width: 1280, height: 900 });
    const page = await ctx.newPage();
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.locator(".goal").first().click();
    await page.locator(".section__actions > .ghost-button").first().click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: join(OUT, `${theme}-form.png`) });
    await page.locator(".primary-button").click();
    await page.locator(".result:not(.result--skeleton)").first().waitFor();
    await page.locator(".meet__button").first().click();
    await page.locator(".beacon").waitFor();
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(OUT, `${theme}-beacon.png`) });
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    await page.screenshot({ path: join(OUT, `${theme}-results-meet.png`) });

    await page.goto(`${BASE}/?view=organizer`, { waitUntil: "networkidle" });
    await page.locator(".map svg").waitFor();
    await page.waitForTimeout(500);
    const map = page.locator(".map").first();
    await map.scrollIntoViewIfNeeded();
    const point = page.locator(".map__point circle:nth-child(2)").nth(40);
    await point.hover();
    await page.waitForTimeout(300);
    await map.screenshot({ path: join(OUT, `${theme}-map.png`) });
    await page.locator(".schedule").screenshot({ path: join(OUT, `${theme}-schedule.png`) });
    await ctx.close();
  }
  const mobile = await context(browser, "dark", { width: 390, height: 844 });
  const page = await mobile.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.locator(".goal").nth(1).click();
  await page.locator(".section__actions > .ghost-button").first().click();
  await page.locator(".primary-button").click();
  await page.locator(".result:not(.result--skeleton)").first().waitFor();
  await page.locator(".meet__button").first().click();
  await page.locator(".beacon").waitFor();
  await page.waitForTimeout(400);
  await page.screenshot({ path: join(OUT, "mobile-beacon.png") });
  await mobile.close();
} finally {
  await browser.close();
}
console.log(`скриншоты: ${OUT}`);
