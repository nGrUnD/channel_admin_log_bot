from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from telethon.errors import FloodWaitError, RPCError

from app.config import settings
from app.db import AdminLogEventRow, get_last_event_id, insert_event, set_last_event_id
from app.services.events import parse_admin_log_event

if TYPE_CHECKING:
    from telethon import TelegramClient

    from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


class AdminLogCollector:
    def __init__(
        self,
        client: TelegramClient,
        notifier: NotificationService,
    ) -> None:
        self._client = client
        self._notifier = notifier
        self._channel_username = settings.channel_username
        self._poll_interval = settings.poll_interval_seconds
        self._backfill_limit = settings.initial_backfill_limit
        self._channel_id: int | None = None
        self._backoff_seconds = 0

    async def run(self) -> None:
        logger.info(
            "Admin log collector: канал %s, интервал %ss",
            self._channel_username,
            self._poll_interval,
        )
        while True:
            try:
                await self._sync_once()
                self._backoff_seconds = 0
            except FloodWaitError as exc:
                self._backoff_seconds = max(exc.seconds + 1, self._poll_interval)
                logger.warning(
                    "FloodWait %ss — пауза перед следующим sync",
                    self._backoff_seconds,
                )
            except RPCError as exc:
                self._backoff_seconds = min(max(self._poll_interval, 60), 300)
                logger.error("Telethon RPC error: %s", exc, exc_info=True)
            except Exception:
                self._backoff_seconds = self._poll_interval
                logger.exception("Admin log sync failed")

            sleep_for = self._backoff_seconds or self._poll_interval
            await asyncio.sleep(sleep_for)

    async def _resolve_channel(self) -> int:
        if self._channel_id is not None:
            return self._channel_id
        entity = await self._client.get_entity(self._channel_username)
        self._channel_id = entity.id
        return self._channel_id

    async def _sync_once(self) -> None:
        channel_id = await self._resolve_channel()
        last_event_id = await get_last_event_id(channel_id)
        is_backfill = last_event_id == 0

        kwargs: dict = {
            "entity": self._channel_username,
            "max_id": 0,
        }
        if is_backfill:
            kwargs["limit"] = self._backfill_limit
            kwargs["min_id"] = 0
        else:
            kwargs["limit"] = 100
            kwargs["min_id"] = last_event_id

        events = []
        async for event in self._client.iter_admin_log(**kwargs):
            events.append(event)

        if not events:
            if is_backfill:
                logger.info("Backfill: событий в admin log не найдено")
            return

        events.sort(key=lambda e: e.id)
        max_event_id = last_event_id
        inserted_count = 0

        for event in events:
            action_type, payload, _, _, _ = parse_admin_log_event(event)
            actor = getattr(event, "user", None)
            actor_id = getattr(actor, "id", None) if actor else None
            actor_username = getattr(actor, "username", None) if actor else None
            actor_parts = []
            if actor:
                if getattr(actor, "first_name", None):
                    actor_parts.append(actor.first_name)
                if getattr(actor, "last_name", None):
                    actor_parts.append(actor.last_name)
            actor_display = " ".join(actor_parts).strip() or None

            inserted = await insert_event(
                event_id=event.id,
                channel_id=channel_id,
                event_date=event.date,
                actor_user_id=actor_id,
                actor_username=actor_username,
                actor_display_name=actor_display,
                action_type=action_type,
                action_payload=payload,
            )
            if inserted:
                inserted_count += 1
                if not is_backfill:
                    row = AdminLogEventRow(
                        event_id=event.id,
                        channel_id=channel_id,
                        event_date=event.date,
                        actor_user_id=actor_id,
                        actor_username=actor_username,
                        actor_display_name=actor_display,
                        action_type=action_type,
                        action_payload=payload,
                    )
                    await self._notifier.notify_if_needed(row)

            if event.id > max_event_id:
                max_event_id = event.id

        if max_event_id > last_event_id:
            await set_last_event_id(channel_id, max_event_id)

        if is_backfill:
            logger.info(
                "Backfill завершён: сохранено %s событий, last_event_id=%s",
                inserted_count,
                max_event_id,
            )
        elif inserted_count:
            logger.info(
                "Sync: %s новых событий, last_event_id=%s",
                inserted_count,
                max_event_id,
            )
