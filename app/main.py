from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.collectors.admin_log import AdminLogCollector
from app.config import settings
from app.telethon_client import connection_help_text, create_telegram_client
from app.db import close_db, init_db
from app.handlers import router
from app.middlewares import AdminOnlyMiddleware
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


def _configure_asyncio_on_windows() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


async def _run() -> None:
    if not settings.admin_ids:
        raise SystemExit("ADMIN_IDS не задан — укажите хотя бы один Telegram ID админа")

    if not settings.telegram_session.strip():
        raise SystemExit(
            "TELEGRAM_SESSION пуст — выполните: python scripts/create_session.py"
        )

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    admin_guard = AdminOnlyMiddleware()
    dp.message.middleware(admin_guard)
    dp.callback_query.middleware(admin_guard)
    dp.include_router(router)

    try:
        telethon_client = create_telegram_client(
            session=settings.telegram_session,
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )
    except ValueError as exc:
        raise SystemExit(f"Ошибка настройки Telethon proxy: {exc}") from exc

    try:
        await telethon_client.connect()
    except (TimeoutError, OSError, asyncio.TimeoutError) as exc:
        raise SystemExit(
            f"Telethon: не удалось подключиться ({type(exc).__name__}).\n\n"
            f"{connection_help_text()}"
        ) from exc
    if not await telethon_client.is_user_authorized():
        await telethon_client.disconnect()
        raise SystemExit(
            "Telethon-сессия не авторизована — пересоздайте через scripts/create_session.py"
        )

    notifier = NotificationService(bot)
    collector = AdminLogCollector(telethon_client, notifier)
    sync_task = asyncio.create_task(collector.run())

    logger.info(
        "Запуск: канал=%s, admins=%s, poll=%ss",
        settings.channel_username,
        settings.admin_ids,
        settings.poll_interval_seconds,
    )

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
        await close_db()
        await telethon_client.disconnect()
        await bot.session.close()


def main() -> None:
    _configure_asyncio_on_windows()
    _configure_logging()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
