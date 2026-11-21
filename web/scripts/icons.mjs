// Рендерит PNG-иконки из public/favicon.svg через установленный Chrome.
//
//   node scripts/icons.mjs
//
// apple-touch-icon.png (180×180) — для «На экран Домой» и превью ссылок:
// знак на белом фоне с полями, скругление углов iOS добавляет сама.

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const svg = await readFile(new URL("../public/favicon.svg", import.meta.url), "utf8");
const browser = await chromium.launch({ channel: "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 180, height: 180 }, colorScheme: "light" });
  await page.setContent(`<body style="margin:0;display:grid;place-items:center;width:180px;height:180px;background:#fff">
    <div style="width:128px;height:128px">${svg.replace("<svg ", '<svg width="128" height="128" ')}</div></body>`);
  await page.screenshot({ path: fileURLToPath(new URL("../public/apple-touch-icon.png", import.meta.url)) });
} finally {
  await browser.close();
}
console.log("public/apple-touch-icon.png");
