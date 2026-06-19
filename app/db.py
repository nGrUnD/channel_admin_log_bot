from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


@dataclass(frozen=True)
class AdminLogEventRow:
    event_id: int
    channel_id: int
    event_date: datetime
    actor_user_id: int | None
    actor_username: str | None
    actor_display_name: str | None
    action_type: str
    action_payload: dict[str, Any]


def _ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def init_db() -> None:
    global _db
    if _db is not None:
        return

    db_path = settings.database_path
    _ensure_parent_dir(db_path)
    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row

    await _db.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_log_events (
            event_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            actor_user_id INTEGER,
            actor_username TEXT,
            actor_display_name TEXT,
            action_type TEXT NOT NULL,
            action_payload TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    await _db.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            channel_id INTEGER PRIMARY KEY,
            last_event_id INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    await _db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_log_events_date
        ON admin_log_events (event_date DESC)
        """
    )
    await _db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_log_events_action_type
        ON admin_log_events (action_type, event_date DESC)
        """
    )
    await _db.commit()
    logger.info("SQLite: %s", db_path)


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def _connection() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database is not initialized")
    return _db


def _row_to_event(row: aiosqlite.Row) -> AdminLogEventRow:
    payload_raw = row["action_payload"] or "{}"
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        payload = {}
    return AdminLogEventRow(
        event_id=int(row["event_id"]),
        channel_id=int(row["channel_id"]),
        event_date=_parse_dt(row["event_date"]),
        actor_user_id=row["actor_user_id"],
        actor_username=row["actor_username"],
        actor_display_name=row["actor_display_name"],
        action_type=row["action_type"],
        action_payload=payload if isinstance(payload, dict) else {},
    )


async def insert_event(
    *,
    event_id: int,
    channel_id: int,
    event_date: datetime,
    actor_user_id: int | None,
    actor_username: str | None,
    actor_display_name: str | None,
    action_type: str,
    action_payload: dict[str, Any],
) -> bool:
    """Returns True if a new row was inserted."""
    conn = _connection()
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    cursor = await conn.execute(
        """
        INSERT OR IGNORE INTO admin_log_events (
            event_id, channel_id, event_date,
            actor_user_id, actor_username, actor_display_name,
            action_type, action_payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            channel_id,
            event_date.isoformat(),
            actor_user_id,
            actor_username,
            actor_display_name,
            action_type,
            json.dumps(action_payload, ensure_ascii=False),
        ),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def get_last_event_id(channel_id: int) -> int:
    conn = _connection()
    cursor = await conn.execute(
        "SELECT last_event_id FROM sync_state WHERE channel_id = ?",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return 0
    return int(row["last_event_id"])


async def set_last_event_id(channel_id: int, last_event_id: int) -> None:
    conn = _connection()
    await conn.execute(
        """
        INSERT INTO sync_state (channel_id, last_event_id)
        VALUES (?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET last_event_id = excluded.last_event_id
        """,
        (channel_id, last_event_id),
    )
    await conn.commit()


async def fetch_recent_events(
    *,
    limit: int = 20,
    action_type: str | None = None,
) -> list[AdminLogEventRow]:
    conn = _connection()
    if action_type:
        cursor = await conn.execute(
            """
            SELECT * FROM admin_log_events
            WHERE action_type = ?
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (action_type, limit),
        )
    else:
        cursor = await conn.execute(
            """
            SELECT * FROM admin_log_events
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (limit,),
        )
    rows = await cursor.fetchall()
    return [_row_to_event(row) for row in rows]


async def fetch_events_for_user(
    *,
    user_id: int | None = None,
    username: str | None = None,
    limit: int = 30,
) -> list[AdminLogEventRow]:
    conn = _connection()
    username_norm = username.lstrip("@").lower() if username else None

    cursor = await conn.execute(
        """
        SELECT * FROM admin_log_events
        ORDER BY event_id DESC
        LIMIT 5000
        """
    )
    rows = await cursor.fetchall()
    matched: list[AdminLogEventRow] = []
    for row in rows:
        event = _row_to_event(row)
        payload = event.action_payload
        target_id = payload.get("target_user_id")
        target_username = (payload.get("target_username") or "").lower()
        actor_username = (event.actor_username or "").lower()

        hit = False
        if user_id is not None:
            if event.actor_user_id == user_id or target_id == user_id:
                hit = True
        if username_norm:
            if actor_username == username_norm or target_username == username_norm:
                hit = True
        if hit:
            matched.append(event)
            if len(matched) >= limit:
                break
    return matched


async def fetch_stats(*, days: int = 7) -> dict[str, Any]:
    conn = _connection()
    cursor = await conn.execute(
        """
        SELECT action_type, COUNT(*) AS cnt
        FROM admin_log_events
        WHERE event_date >= datetime('now', ?)
        GROUP BY action_type
        ORDER BY cnt DESC
        """,
        (f"-{days} days",),
    )
    week_rows = await cursor.fetchall()
    week_stats = {row["action_type"]: int(row["cnt"]) for row in week_rows}

    cursor = await conn.execute(
        """
        SELECT action_type, COUNT(*) AS cnt
        FROM admin_log_events
        WHERE date(event_date) = date('now')
        GROUP BY action_type
        ORDER BY cnt DESC
        """
    )
    today_rows = await cursor.fetchall()
    today_stats = {row["action_type"]: int(row["cnt"]) for row in today_rows}

    cursor = await conn.execute("SELECT COUNT(*) AS total FROM admin_log_events")
    total_row = await cursor.fetchone()
    total = int(total_row["total"]) if total_row else 0

    return {
        "total": total,
        "today": today_stats,
        "week": week_stats,
    }
