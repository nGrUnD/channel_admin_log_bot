from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import settings
from app.db import AdminLogEventRow
from app.services.events import format_event_line

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._notify_types = frozenset(settings.notify_event_types)
        self._recipient_ids = settings.effective_notify_ids()

    async def notify_if_needed(self, event: AdminLogEventRow) -> None:
        if event.action_type not in self._notify_types:
            return
        if not self._recipient_ids:
            logger.warning("ADMIN_NOTIFY_IDS пуст — уведомления не отправляются")
            return

        text = (
            "<b>Новое событие в канале</b>\n"
            f"{format_event_line(event)}"
        )
        for admin_id in self._recipient_ids:
            try:
                await self._bot.send_message(admin_id, text)
            except TelegramAPIError as exc:
                logger.warning(
                    "Не удалось отправить уведомление admin_id=%s: %s",
                    admin_id,
                    exc,
                )
