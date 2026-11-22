// Клиент личной ленты заказов Orunt (long-poll). Node 20+, без зависимостей.
//   export ORUNT_API_KEY=orunt_...
//   node poll.mjs
import { readFileSync, writeFileSync, renameSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const BASE_URL = (process.env.ORUNT_BASE_URL ?? "https://orunt.pro").replace(/\/+$/, "");
const CURSOR_FILE = process.env.ORUNT_CURSOR_FILE ?? "orunt_cursor.txt";
const KEY = process.env.ORUNT_API_KEY;
const WAIT_SECONDS = 50; // сервер принимает 0-60
const BACKOFF_STEPS = [5, 10, 20, 60]; // секунды

if (!KEY) {
  console.error("Задайте ORUNT_API_KEY (ключ: бот @oruntbot, Настройки -> API).");
  process.exit(1);
}

function loadCursor() {
  try {
    return readFileSync(CURSOR_FILE, "utf8").trim() || null;
  } catch {
    return null;
  }
}

function saveCursor(cursor) {
  writeFileSync(`${CURSOR_FILE}.tmp`, cursor);
  renameSync(`${CURSOR_FILE}.tmp`, CURSOR_FILE);
}

function onOrder(order) {
  const budget = order.budget == null ? "бюджет не указан" : `${order.budget} ${order.currency ?? ""}`.trim();
  console.log(`[${order.source}] ${order.title} (${budget})\n  ${order.url}`);
}

let cursor = loadCursor();
let attempt = 0;
const backoff = async () => {
  await sleep(BACKOFF_STEPS[Math.min(attempt, BACKOFF_STEPS.length - 1)] * 1000);
  attempt += 1;
};

while (true) {
  const params = new URLSearchParams({ wait: String(WAIT_SECONDS) });
  if (cursor) params.set("since", cursor);

  let res;
  try {
    res = await fetch(`${BASE_URL}/api/v1/me/orders?${params}`, {
      headers: { Authorization: `Bearer ${KEY}` }, // ключ только в заголовке
      signal: AbortSignal.timeout(70_000), // больше WAIT_SECONDS
    });
  } catch (err) {
    console.error(`Сеть недоступна: ${err.message}`);
    await backoff();
    continue;
  }

  if (res.status === 401 || res.status === 403) {
    // 401: ключ неверный/перевыпущен/отозван; 403 plan_required: нет PRO.
    console.error(`Остановка: HTTP ${res.status} ${await res.text()}`);
    process.exit(1);
  }
  if (res.status === 400) {
    console.error(`Остановка: неверные параметры или курсор, HTTP 400 ${await res.text()}`);
    process.exit(1);
  }
  if (res.status === 409 || res.status === 429) {
    // 409: уже идёт long-poll с этим ключом; 429: лимит запросов.
    const delay = Number(res.headers.get("Retry-After") ?? "15") || 15;
    console.error(`HTTP ${res.status}, пауза ${delay} с`);
    await sleep(delay * 1000);
    continue;
  }
  if (!res.ok) {
    // 502/503/504: сервер обновляется (обычно 10-30 с). Курсор не теряем.
    console.error(`HTTP ${res.status}, повтор с паузой`);
    await backoff();
    continue;
  }

  attempt = 0;
  const data = await res.json();
  for (const order of data.orders) onOrder(order);
  cursor = data.next_cursor;
  saveCursor(cursor);
}
