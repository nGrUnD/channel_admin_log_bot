#!/usr/bin/env bash
# Первичная установка на Linux-сервере (Ubuntu/Debian).
# Запуск из корня репозитория:
#   chmod +x scripts/setup_server.sh scripts/deploy.sh
#   ./scripts/setup_server.sh
#
# Перед запуском положите .env в корень проекта (скопируйте с .env.example).
# TELEGRAM_SESSION можно создать на сервере: python scripts/create_session.py

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE_NAME="${SYSTEMD_SERVICE:-channel-admin-log-bot.service}"
SERVICE_USER="${SERVICE_USER:-$USER}"
APP_DIR="${APP_DIR:-$ROOT}"

echo "==> Установка в: $APP_DIR"
echo "==> Пользователь systemd: $SERVICE_USER"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 не найден. Ubuntu/Debian:"
  echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip git"
  exit 1
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "Создан .env из .env.example — заполните его перед запуском."
  else
    echo "Нет .env — создайте файл с переменными окружения."
    exit 1
  fi
fi

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

mkdir -p data

if [[ -z "${TELEGRAM_SESSION:-}" ]] && ! grep -q '^TELEGRAM_SESSION=.\+' .env 2>/dev/null; then
  echo
  echo "TELEGRAM_SESSION пуст. На сервере выполните один раз:"
  echo "  cd $APP_DIR && venv/bin/python scripts/create_session.py"
  echo "и добавьте строку в .env"
  echo
fi

UNIT_DST="/etc/systemd/system/$SERVICE_NAME"
UNIT_SRC="$ROOT/scripts/channel-admin-log-bot.service.example"

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Не найден $UNIT_SRC"
  exit 1
fi

TMP_UNIT="$(mktemp)"
sed \
  -e "s|__USER__|$SERVICE_USER|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$UNIT_SRC" > "$TMP_UNIT"

echo "==> Установка systemd unit: $UNIT_DST"
sudo cp "$TMP_UNIT" "$UNIT_DST"
rm -f "$TMP_UNIT"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo
echo "Готово. Дальше:"
echo "  1. Проверьте .env в $APP_DIR"
echo "  2. sudo systemctl start $SERVICE_NAME"
echo "  3. sudo journalctl -u $SERVICE_NAME -f"
