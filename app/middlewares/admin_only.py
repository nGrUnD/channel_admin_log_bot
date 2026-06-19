from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import settings

logger = logging.getLogger(__name__)


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        else:
            from_user = getattr(event, "from_user", None)
            user = from_user

        if user is None:
            return None

        if user.id not in settings.admin_ids:
            if isinstance(event, Message):
                await event.answer("Доступ запрещён.")
            else:
                answer = getattr(event, "answer", None)
                if callable(answer):
                    await answer("Доступ запрещён.", show_alert=True)
            logger.info("Отклонён доступ user_id=%s", user.id)
            return None

        return await handler(event, data)
