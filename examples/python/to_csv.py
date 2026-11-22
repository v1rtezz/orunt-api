#!/usr/bin/env python3
"""Складывает новые заказы личной ленты Orunt в CSV-файл.

Использует poll_orders.py из этой же папки. Переменные окружения:
ORUNT_API_KEY (обязательна), ORUNT_CSV_FILE (по умолчанию orders.csv),
ORUNT_CURSOR_FILE, ORUNT_BASE_URL.
"""
import csv
import os

from poll_orders import run

CSV_FILE = os.environ.get("ORUNT_CSV_FILE", "orders.csv")
FIELDS = ["id", "source", "title", "budget", "currency", "category", "published_at", "created_at", "url"]


def append_order(order):
    new_file = not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerow({name: order.get(name) for name in FIELDS})
    print(f"+ {order['id']} {order['title']}", flush=True)


if __name__ == "__main__":
    try:
        run(append_order)
    except KeyboardInterrupt:
        pass
