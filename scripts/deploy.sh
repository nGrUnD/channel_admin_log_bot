#!/usr/bin/env bash
# Обновление на сервере: pull (если git) + pip + restart systemd.
# Запуск: ./scripts/deploy.sh
# Другое имя юнита: SYSTEMD_SERVICE=my-bot.service ./scripts/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE="${SYSTEMD_SERVICE:-channel-admin-log-bot.service}"

if [[ -d .git ]]; then
  git pull
else
  echo "Не git-репозиторий — пропускаем git pull"
fi

if [[ ! -x venv/bin/pip ]]; then
  echo "Нет venv — сначала: ./scripts/setup_server.sh"
  exit 1
fi

venv/bin/pip install -r requirements.txt
mkdir -p data

sudo systemctl restart "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager -l
