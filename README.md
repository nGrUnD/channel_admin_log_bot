# Channel Admin Log Bot

Telegram-бот, который собирает и хранит события из раздела **«Недавние действия»** админ-панели канала: вступления, выходы, баны, правки сообщений и др.

## Почему нужны два компонента

Bot API **не отдаёт** admin log. Для чтения «Недавних действий» используется **Telethon (MTProto)** с user-сессией аккаунта-админа канала. Сам бот (aiogram) нужен для команд просмотра и push-уведомлений админам.

## Требования

- Python 3.11+
- Аккаунт Telegram с правами **администратора** в целевом канале
- `api_id` / `api_hash` с [my.telegram.org](https://my.telegram.org)
- Токен бота от [@BotFather](https://t.me/BotFather)

## Установка

```bash
cd channel_admin_log_bot
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # заполните переменные
```

## Настройка

1. Скопируйте `.env.example` → `.env` и заполните `BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `CHANNEL_USERNAME`, `ADMIN_IDS`.
2. Создайте Telethon-сессию (один раз):

```bash
python scripts/create_session.py
```

Скопируйте выведенный `TELEGRAM_SESSION` в `.env`.

Если `create_session.py` выдаёт **TimeoutError** — это блокировка MTProto в сети (Bot API при этом может работать). Включите VPN и укажите прокси в `.env`:

```env
TELEGRAM_PROXY_TYPE=socks5
TELEGRAM_PROXY_HOST=127.0.0.1
TELEGRAM_PROXY_PORT=1080
```

Порт и тип смотрите в настройках вашего VPN-клиента (Clash, V2Ray, Hiddify и т.д.).

3. Убедитесь, что **user-аккаунт сессии** — админ канала (достаточно права просмотра admin log).
4. Запустите бота и напишите ему `/start` из аккаунта, чей ID указан в `ADMIN_IDS`.

## Запуск локально

```bash
python -m app
```

При первом запуске загружаются последние `INITIAL_BACKFILL_LIMIT` (по умолчанию 500) событий **без уведомлений**. Далее каждые `POLL_INTERVAL_SECONDS` секунд подтягиваются новые события; по настраиваемым типам отправляются уведомления в личку админам.

## Деплой на Linux-сервер

На VPS MTProto обычно работает без прокси — `create_session.py` удобнее запускать прямо на сервере.

### 1. Скопируйте проект на сервер

```bash
# с вашего ПК (пример)
scp -r channel_admin_log_bot user@your-server:~/
```

Или через git:

```bash
ssh user@your-server
git clone <url> ~/channel_admin_log_bot
cd ~/channel_admin_log_bot
```

### 2. Настройте `.env`

```bash
cp .env.example .env
nano .env
```

Заполните `BOT_TOKEN`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `CHANNEL_USERNAME`, `ADMIN_IDS`.

### 3. Создайте Telethon-сессию на сервере

```bash
chmod +x scripts/setup_server.sh scripts/deploy.sh
./scripts/setup_server.sh          # venv + systemd unit
venv/bin/python scripts/create_session.py
nano .env                          # вставьте TELEGRAM_SESSION
```

### 4. Запустите как службу

```bash
sudo systemctl start channel-admin-log-bot
sudo systemctl status channel-admin-log-bot
sudo journalctl -u channel-admin-log-bot -f
```

### Обновление

```bash
./scripts/deploy.sh
```

Переменные для `setup_server.sh`:

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SERVICE_USER` | текущий пользователь | User в systemd |
| `APP_DIR` | корень репозитория | Путь к проекту |
| `SYSTEMD_SERVICE` | `channel-admin-log-bot.service` | Имя unit-файла |

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start`, `/help` | Справка |
| `/recent [N]` | Последние N событий (20 по умолчанию, макс. 50) |
| `/joins [N]` | Только вступления |
| `/leaves [N]` | Только выходы |
| `/stats` | Сводка за сегодня и 7 дней |
| `/user <id\|@username>` | События, связанные с пользователем |

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен aiogram-бота |
| `TELEGRAM_API_ID` | API ID с my.telegram.org |
| `TELEGRAM_API_HASH` | API Hash |
| `TELEGRAM_SESSION` | StringSession после `create_session.py` |
| `CHANNEL_USERNAME` | `@channel` или `channel` |
| `ADMIN_IDS` | ID админов бота через запятую |
| `ADMIN_NOTIFY_IDS` | Кому слать уведомления (по умолчанию = `ADMIN_IDS`) |
| `NOTIFY_EVENT_TYPES` | Типы для push: `join,leave,ban,kick,unban` |
| `POLL_INTERVAL_SECONDS` | Интервал опроса admin log (30) |
| `INITIAL_BACKFILL_LIMIT` | Сколько событий загрузить при первом запуске (500) |
| `DATABASE_PATH` | Путь к SQLite (`data/bot.db`) |
| `TELEGRAM_PROXY_TYPE` | `socks5`, `http` или `mtproxy` (если MTProto заблокирован) |
| `TELEGRAM_PROXY_HOST` | Хост прокси, часто `127.0.0.1` |
| `TELEGRAM_PROXY_PORT` | Порт прокси |
| `TELEGRAM_MTPROXY_SECRET` | Секрет для MTProxy |
| `TELEGRAM_CONNECT_TIMEOUT` | Таймаут подключения Telethon в секундах (30) |

## Структура

```
app/
  main.py                 # Telethon sync + aiogram polling
  collectors/admin_log.py # сбор событий
  handlers/log.py         # команды бота
  services/               # форматирование и уведомления
  db.py                   # SQLite
scripts/create_session.py
```

Данные хранятся локально в SQLite. Дубликаты отсекаются по `event_id` из Telegram.
