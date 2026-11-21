// Скриншоты интерфейса для проверки дизайна и презентации.
//
//   KOPIR_URL=http://localhost:8000 OUT=./screenshots node scripts/screenshots.mjs
//
// Использует установленный Google Chrome (playwright-core, channel "chrome"),
// отдельный браузер не скачивается. Сценарий: цель → «Заполнить примером» → подбор.

import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "playwright-core";

const BASE = process.env.KOPIR_URL ?? "http://localhost:8000";
const OUT = process.env.OUT ?? "screenshots";
const LANG = process.env.KOPIR_LANG ?? "ru";
const GOAL_INDEX = Number(process.env.KOPIR_GOAL ?? 0); // 0 — «Найти работу»

const VIEWPORTS = {
  desktop: { width: 1280, height: 900 },
  mobile: { width: 390, height: 844 },
};

async function shoot(browser, theme, device) {
  const context = await browser.newContext({ viewport: VIEWPORTS[device], deviceScaleFactor: 2 });
  await context.addInitScript(
    ([t, lang]) => {
      localStorage.clear();
      localStorage.setItem("kopir.theme", JSON.stringify(t));
      localStorage.setItem("kopir.lang", JSON.stringify(lang));
    },
    [theme, LANG],
  );
  const page = await context.newPage();
  const name = (step) => join(OUT, `${device}-${theme}-${step}.png`);

  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.screenshot({ path: name("1-landing") });

  await page.locator(".goal").nth(GOAL_INDEX).click();
  await page.locator(".section .ghost-button").first().click();
  await page.waitForTimeout(600); // анимация появления секций
  await page.screenshot({ path: name("2-form"), fullPage: true });

  await page.locator(".primary-button").click();
  await page.locator(".result:not(.result--skeleton)").first().waitFor();
  await page.waitForTimeout(900); // анимация колец
  await page.screenshot({ path: name("3-results"), fullPage: true });
  await context.close();
}

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch({ channel: "chrome" });
try {
  for (const theme of ["light", "dark"]) {
    for (const device of Object.keys(VIEWPORTS)) await shoot(browser, theme, device);
  }
} finally {
  await browser.close();
}
console.log(`скриншоты: ${OUT}`);
