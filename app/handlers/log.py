from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.db import fetch_events_for_user, fetch_recent_events, fetch_stats
from app.services.events import format_events_message, format_stats

router = Router(name="log")

HELP_TEXT = (
    "<b>Бот «Недавние действия» канала</b>\n\n"
    "Команды:\n"
    "/recent [N] — последние события (по умолчанию 20, макс. 50)\n"
    "/joins [N] — только вступления\n"
    "/leaves [N] — только выходы\n"
    "/stats — сводка за сегодня и 7 дней\n"
    "/user &lt;id|@username&gt; — события пользователя\n"
    "/help — эта справка"
)


def _parse_limit(args: str | None, *, default: int = 20, maximum: int = 50) -> int:
    if not args:
        return default
    parts = args.strip().split()
    if not parts:
        return default
    try:
        value = int(parts[0])
    except ValueError:
        return default
    return max(1, min(value, maximum))


@router.message(Command("start", "help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("recent"))
async def cmd_recent(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command.args)
    events = await fetch_recent_events(limit=limit)
    text = format_events_message(events, title=f"Последние {limit} событий")
    await message.answer(text)


@router.message(Command("joins"))
async def cmd_joins(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command.args)
    events = await fetch_recent_events(limit=limit, action_type="join")
    text = format_events_message(events, title=f"Вступления ({limit})")
    await message.answer(text)


@router.message(Command("leaves"))
async def cmd_leaves(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command.args)
    events = await fetch_recent_events(limit=limit, action_type="leave")
    text = format_events_message(events, title=f"Выходы ({limit})")
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    stats = await fetch_stats(days=7)
    await message.answer(format_stats(stats))


@router.message(Command("user"))
async def cmd_user(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    if not args:
        await message.answer("Укажите пользователя: /user 123456789 или /user @username")
        return

    user_id: int | None = None
    username: str | None = None

    if args.isdigit():
        user_id = int(args)
    elif args.startswith("@"):
        username = args[1:]
    elif re.fullmatch(r"id\d+", args, re.IGNORECASE):
        user_id = int(args[2:])
    else:
        username = args.lstrip("@")

    events = await fetch_events_for_user(
        user_id=user_id,
        username=username,
        limit=30,
    )
    query_label = args
    text = format_events_message(events, title=f"События: {query_label}")
    await message.answer(text)
