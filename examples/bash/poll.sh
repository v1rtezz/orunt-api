#!/usr/bin/env bash
# Клиент личной ленты заказов Orunt (long-poll): curl + jq.
#   export ORUNT_API_KEY=orunt_...
#   ./poll.sh
set -u

BASE_URL="${ORUNT_BASE_URL:-https://orunt.pro}"
CURSOR_FILE="${ORUNT_CURSOR_FILE:-orunt_cursor.txt}"
WAIT=50 # сервер принимает 0-60
BACKOFF=(5 10 20 60)

: "${ORUNT_API_KEY:?Задайте ORUNT_API_KEY (ключ: бот @oruntbot, Настройки -> API)}"
command -v jq >/dev/null || { echo "Нужен jq" >&2; exit 1; }

BODY="$(mktemp)"
HEADERS="$(mktemp)"
trap 'rm -f "$BODY" "$HEADERS"' EXIT

cursor=""
[ -f "$CURSOR_FILE" ] && cursor="$(tr -d '[:space:]' < "$CURSOR_FILE")"
attempt=0

backoff() {
  local i=$attempt
  [ "$i" -ge "${#BACKOFF[@]}" ] && i=$((${#BACKOFF[@]} - 1))
  sleep "${BACKOFF[$i]}"
  attempt=$((attempt + 1))
}

while true; do
  args=(-sS --max-time 70 -o "$BODY" -D "$HEADERS" -w '%{http_code}'
        -H "Authorization: Bearer $ORUNT_API_KEY" -G
        --data-urlencode "wait=$WAIT")
  [ -n "$cursor" ] && args+=(--data-urlencode "since=$cursor")

  status="$(curl "${args[@]}" "$BASE_URL/api/v1/me/orders")" || status=000

  case "$status" in
    200)
      attempt=0
      jq -r '.orders[] | "[\(.source)] \(.title) (\(.budget // "бюджет не указан") \(.currency // ""))\n  \(.url)"' "$BODY"
      new_cursor="$(jq -r '.next_cursor' "$BODY")"
      if [ -n "$new_cursor" ] && [ "$new_cursor" != "null" ]; then
        cursor="$new_cursor"
        printf '%s' "$cursor" > "$CURSOR_FILE.tmp" && mv "$CURSOR_FILE.tmp" "$CURSOR_FILE"
      fi
      ;;
    401|403|400)
      echo "Остановка: HTTP $status $(cat "$BODY")" >&2
      exit 1
      ;;
    409|429)
      delay="$(grep -i '^retry-after:' "$HEADERS" | tr -d '\r' | awk '{print $2}')"
      delay="${delay:-15}"
      echo "HTTP $status, пауза $delay с" >&2
      sleep "$delay"
      ;;
    *)
      echo "HTTP $status (сеть или обновление сервера), повтор с паузой" >&2
      backoff
      ;;
  esac
done
