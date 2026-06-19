"""One-time Telethon authorization → StringSession for .env TELEGRAM_SESSION."""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from telethon.errors import RPCError

load_dotenv()

# Allow running as `python scripts/create_session.py` from project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.telethon_client import connection_help_text, create_telegram_client


async def main() -> None:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id or not api_hash:
        print("Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в .env или окружении.")
        sys.exit(1)

    try:
        client = create_telegram_client(
            session="",
            api_id=int(api_id),
            api_hash=api_hash,
        )
    except ValueError as exc:
        print(f"Ошибка настройки прокси: {exc}")
        sys.exit(1)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.start()
        session_string = client.session.save()
    except (TimeoutError, OSError, asyncio.TimeoutError, RPCError) as exc:
        print(f"Ошибка подключения: {type(exc).__name__}: {exc}\n")
        print(connection_help_text())
        sys.exit(1)
    finally:
        if client.is_connected():
            await client.disconnect()

    print("\nАвторизация успешна. Добавьте в .env:\n")
    print(f"TELEGRAM_SESSION={session_string}\n")
    print("User-аккаунт этой сессии должен быть админом целевого канала.")


if __name__ == "__main__":
    asyncio.run(main())
