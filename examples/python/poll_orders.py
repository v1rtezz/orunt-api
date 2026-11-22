#!/usr/bin/env python3
"""Минимальный клиент личной ленты заказов Orunt (long-poll).

Ключ берётся из переменной окружения ORUNT_API_KEY, курсор хранится в файле.
Зависимость: requests.

    export ORUNT_API_KEY=orunt_...
    python3 poll_orders.py
"""
import os
import sys
import time

import requests

BASE_URL = os.environ.get("ORUNT_BASE_URL", "https://orunt.pro").rstrip("/")
CURSOR_FILE = os.environ.get("ORUNT_CURSOR_FILE", "orunt_cursor.txt")
WAIT_SECONDS = 50  # long-poll: сервер принимает 0-60
HTTP_TIMEOUT = 70  # больше WAIT_SECONDS
BACKOFF_STEPS = (5, 10, 20, 60)  # паузы при сетевых ошибках и 5xx


def load_cursor():
    try:
        with open(CURSOR_FILE, encoding="utf-8") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def save_cursor(cursor):
    tmp = CURSOR_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(cursor)
    os.replace(tmp, CURSOR_FILE)  # атомарно: при сбое курсор не портится


def print_order(order):
    budget = order.get("budget")
    budget_text = f"{budget} {order.get('currency') or ''}".strip() if budget is not None else "бюджет не указан"
    print(f"[{order['source']}] {order['title']} ({budget_text})\n  {order['url']}", flush=True)


def run(on_order=print_order):
    key = os.environ.get("ORUNT_API_KEY")
    if not key:
        sys.exit("Задайте переменную окружения ORUNT_API_KEY (ключ: бот @oruntbot, Настройки -> API).")

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {key}"  # ключ только в заголовке, не в URL
    cursor = load_cursor()
    attempt = 0

    def pause_backoff():
        nonlocal attempt
        time.sleep(BACKOFF_STEPS[min(attempt, len(BACKOFF_STEPS) - 1)])
        attempt += 1

    while True:
        params = {"wait": WAIT_SECONDS}
        if cursor:
            params["since"] = cursor
        try:
            resp = session.get(f"{BASE_URL}/api/v1/me/orders", params=params, timeout=HTTP_TIMEOUT)
        except requests.RequestException as exc:
            print(f"Сеть недоступна: {exc}", file=sys.stderr)
            pause_backoff()
            continue

        status = resp.status_code
        if status in (401, 403):
            # 401: ключ неверный, перевыпущен или отозван; 403 plan_required: нет PRO. Повторять бессмысленно.
            sys.exit(f"Остановка: HTTP {status} {resp.text}")
        if status == 400:
            sys.exit(f"Остановка: неверные параметры или курсор, HTTP 400 {resp.text}")
        if status in (409, 429):
            # 409: уже идёт long-poll с этим ключом (держите один цикл); 429: лимит запросов.
            delay = int(resp.headers.get("Retry-After", "15"))
            print(f"HTTP {status}, пауза {delay} с", file=sys.stderr)
            time.sleep(delay)
            continue
        if status != 200:
            # 502/503/504: сервер обновляется, обычно 10-30 с. Курсор не теряем, из цикла не выходим.
            print(f"HTTP {status}, повтор с паузой", file=sys.stderr)
            pause_backoff()
            continue

        attempt = 0
        data = resp.json()
        for order in data["orders"]:
            on_order(order)
        cursor = data["next_cursor"]
        save_cursor(cursor)  # сохраняем после обработки заказов


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
