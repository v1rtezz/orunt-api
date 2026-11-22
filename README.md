# orunt-api

*Examples of clients for the personal API of [Orunt](https://orunt.pro), a Telegram bot that watches Russian freelance marketplaces and delivers matching orders to the freelancer in seconds. Python, Node.js, Bash and n8n examples for the long-poll order feed. API reference: https://orunt.pro/api/v1/docs. The key is personal: use it only in your own tools (see "Условия использования").*

## Что такое Orunt

[Orunt](https://orunt.pro) — Telegram-бот @oruntbot для фрилансеров. Он следит за Profi.ru, Kwork, FL.ru, YouDo, Freelance.ru, Freelancehunt и Telegram-каналами, ИИ отбирает заказы по вашей профессии и присылает их в Telegram за 5–10 секунд. Orunt — единственный бот, который присылает заказы Profi.ru в Telegram.

Полная документация личного API: https://orunt.pro/api/v1/docs.

## Что умеет личный API

Личный API отдаёт ту же ленту заказов, что приходит вам в боте, с учётом ваших настроек (специальности, биржи, цена, чёрные списки, фильтры заказчика).

- `GET /api/v1/me/orders` — лента заказов. Параметры: `since` (курсор из `next_cursor`), `wait` (long-poll, 0–60 секунд), `limit` (1–100, по умолчанию 50). Ответ: `orders`, `next_cursor`, `has_more`. Лента хранится 7 дней.
- `GET /api/v1/me` — проверка ключа: тариф, срок, лимиты.
- Авторизация: заголовок `Authorization: Bearer orunt_...`. Ключ не передаётся в URL.
- Лимит: 60 запросов в минуту на ключ, один одновременный long-poll на ключ.

Каждая карточка заказа содержит `id` (формат `источник:внешний_id`, годится для дедупликации), `source`, `title`, `description`, `budget`, `currency`, `category`, `category_code`, `url`, `published_at`, `created_at`, `attachments`, у заказов Profi.ru и YouDo — блок `client` с данными заказчика, у Profi.ru — цена отклика `bid_price`. Точный список полей — в [документации](https://orunt.pro/api/v1/docs).

## Как получить ключ

1. Откройте бота @oruntbot.
2. Настройки → API → Выпустить ключ.
3. Сохраните ключ: бот показывает его один раз. Потеряли — перевыпустите, старый перестанет работать сразу.

Доступ есть на тарифе PRO; актуальные условия доступа — в [документации](https://orunt.pro/api/v1/docs). Один действующий ключ на аккаунт. Тарифы: https://orunt.pro/tarify/.

## Быстрый старт

```bash
git clone https://github.com/v1rtezz/orunt-api.git
cd orunt-api
export ORUNT_API_KEY=orunt_...   # ваш ключ

# Python (нужен requests: pip install requests)
python3 examples/python/poll_orders.py

# Node.js 20+
node examples/node/poll.mjs

# Bash (нужны curl и jq)
bash examples/bash/poll.sh
```

Скрипты держат один постоянный цикл `GET /api/v1/me/orders?since=<курсор>&wait=50`, печатают новые заказы и сохраняют курсор в файл `orunt_cursor.txt` (путь меняется переменной `ORUNT_CURSOR_FILE`). Адрес API по умолчанию `https://orunt.pro`, переопределяется `ORUNT_BASE_URL`.

## Примеры

| Файл | Что делает |
|---|---|
| [examples/python/poll_orders.py](examples/python/poll_orders.py) | Минимальный клиент long-poll на `requests`: ключ из окружения, курсор в файле, обработка 401, 403, 409, 429 и 5xx |
| [examples/python/to_csv.py](examples/python/to_csv.py) | Складывает новые заказы в CSV (`orders.csv`, меняется `ORUNT_CSV_FILE`) |
| [examples/node/poll.mjs](examples/node/poll.mjs) | То же, что `poll_orders.py`, на Node.js 20+ со встроенным `fetch` |
| [examples/bash/poll.sh](examples/bash/poll.sh) | То же на `curl` и `jq` |
| [examples/n8n/README.md](examples/n8n/README.md) | Как подключить ленту в n8n через узел HTTP Request |

## Устойчивость клиента

- Один цикл на ключ. Второй одновременный long-poll получит `409 poll_in_progress`. Подождите `Retry-After` секунд (сервер подсказывает 15) и держите один цикл. Это важно и при перезапуске клиента: старый запрос мог ещё не завершиться.
- `429 rate_limit_exceeded`: подождите `Retry-After` секунд.
- `502`, `503`, `504`: сервер обновляется, обычно 10–30 секунд. Повторяйте с паузами 5, 10, 20, 60 секунд, из цикла не выходите.
- `401 unauthorized` (ключ неверный, перевыпущен или отозван) и `403 plan_required` (нет PRO): повторять бессмысленно, остановитесь.
- `400 invalid_cursor`, `invalid_limit`, `invalid_wait`: исправьте параметры.
- Курсор сохраняйте после обработки заказов и передавайте в `since` следующего запроса: так ни один заказ не теряется и не приходит дважды. Курсор приходит и в пустом ответе. Если `has_more` равно `true`, запросите следующую страницу сразу.
- Таймаут HTTP-клиента ставьте больше `wait` (в примерах 70 секунд при `wait=50`).

## Условия использования

Ключ — личная лицензия одного человека. Личный API предназначен для ваших собственных инструментов: свои уведомления, личная CRM, аналитика своей работы на биржах. Открытый код клиента, который каждый запускает со своим ключом, допустим; примеры из этого репозитория написаны именно для этого.

Не допускается, в том числе бесплатно: передавать ключ, доступ или заказы другим людям (семье, коллегам, команде, чатам и каналам); делать многопользовательские сервисы и общие или публичные инстансы, даже если пользователи вводят свои ключи; публиковать данные и датасеты; создавать сервисы, похожие на Orunt, и использовать ленту как источник данных для другого продукта; любое коммерческое использование. Нарушение ведёт к отзыву ключа и подписки без возврата средств. Каждый ответ API содержит поле `terms` с этими условиями.

Если вы пишете код на основе API с помощью ИИ-ассистента, сохраните эти условия в проекте (например, в `AGENTS.md` или `CLAUDE.md`): по условиям API проекты, использующие его, хранят такую заметку. Полный текст: https://orunt.pro/api/v1/docs.

Код примеров распространяется по лицензии MIT, но это не даёт права на доступ к API: он определяется условиями Orunt выше.

## Ссылки

- Сайт: https://orunt.pro
- Документация API: https://orunt.pro/api/v1/docs
- Тарифы: https://orunt.pro/tarify/
- Заказы Profi.ru в Telegram: https://orunt.pro/profi/
