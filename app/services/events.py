from __future__ import annotations

from typing import Any

from telethon.tl.types import (
    ChannelAdminLogEventActionChangeAbout,
    ChannelAdminLogEventActionChangeHistoryTTL,
    ChannelAdminLogEventActionChangeLinkedChat,
    ChannelAdminLogEventActionChangeLocation,
    ChannelAdminLogEventActionChangePhoto,
    ChannelAdminLogEventActionChangeStickerSet,
    ChannelAdminLogEventActionChangeTitle,
    ChannelAdminLogEventActionChangeUsername,
    ChannelAdminLogEventActionCreateTopic,
    ChannelAdminLogEventActionDefaultBannedRights,
    ChannelAdminLogEventActionDeleteMessage,
    ChannelAdminLogEventActionDeleteTopic,
    ChannelAdminLogEventActionDiscardGroupCall,
    ChannelAdminLogEventActionEditMessage,
    ChannelAdminLogEventActionExportedInviteDelete,
    ChannelAdminLogEventActionExportedInviteEdit,
    ChannelAdminLogEventActionExportedInviteRevoke,
    ChannelAdminLogEventActionParticipantInvite,
    ChannelAdminLogEventActionParticipantJoin,
    ChannelAdminLogEventActionParticipantJoinByInvite,
    ChannelAdminLogEventActionParticipantJoinByRequest,
    ChannelAdminLogEventActionParticipantLeave,
    ChannelAdminLogEventActionParticipantMute,
    ChannelAdminLogEventActionParticipantToggleAdmin,
    ChannelAdminLogEventActionParticipantToggleBan,
    ChannelAdminLogEventActionParticipantUnmute,
    ChannelAdminLogEventActionParticipantVolume,
    ChannelAdminLogEventActionPinMessage,
    ChannelAdminLogEventActionSendMessage,
    ChannelAdminLogEventActionStartGroupCall,
    ChannelAdminLogEventActionStopPoll,
    ChannelAdminLogEventActionToggleForum,
    ChannelAdminLogEventActionToggleInvites,
    ChannelAdminLogEventActionToggleNoForwards,
    ChannelAdminLogEventActionTogglePreHistoryHidden,
    ChannelAdminLogEventActionToggleSignatures,
    ChannelAdminLogEventActionToggleSlowMode,
    ChannelAdminLogEventActionUpdatePinned,
    User,
)

ACTION_LABELS: dict[str, str] = {
    "join": "вступил в канал",
    "leave": "покинул канал",
    "invite": "приглашён",
    "ban": "заблокирован",
    "unban": "разблокирован",
    "kick": "исключён",
    "promote": "назначен админом",
    "demote": "снят с админа",
    "edit": "сообщение изменено",
    "delete": "сообщение удалено",
    "pinned": "сообщение закреплено",
    "settings": "изменены настройки",
    "info": "изменена информация канала",
    "send": "отправлено сообщение",
    "group_call": "групповой звонок",
    "forums": "форум",
    "other": "другое действие",
}


def _user_display(user: User | None) -> tuple[int | None, str | None, str | None]:
    if user is None:
        return None, None, None
    user_id = user.id
    username = user.username
    parts = [user.first_name or "", user.last_name or ""]
    display = " ".join(p for p in parts if p).strip() or None
    return user_id, username, display


def _participant_user(action: Any) -> User | None:
    participant = getattr(action, "participant", None)
    if participant is None:
        return None
    user = getattr(participant, "user", None)
    if isinstance(user, User):
        return user
    return None


def parse_admin_log_event(event: Any) -> tuple[str, dict[str, Any], int | None, str | None, str | None]:
    """Returns action_type, payload, target_user_id, target_username, target_display_name."""
    action = event.action
    payload: dict[str, Any] = {}

    actor_id, actor_username, actor_display = _user_display(getattr(event, "user", None))
    if actor_id is not None:
        payload["actor_user_id"] = actor_id
    if actor_username:
        payload["actor_username"] = actor_username
    if actor_display:
        payload["actor_display_name"] = actor_display

    target_user: User | None = None
    action_type = "other"

    if isinstance(action, ChannelAdminLogEventActionParticipantJoin):
        action_type = "join"
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif isinstance(action, ChannelAdminLogEventActionParticipantLeave):
        action_type = "leave"
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif isinstance(action, ChannelAdminLogEventActionParticipantJoinByInvite):
        action_type = "join"
        payload["via_invite"] = True
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif isinstance(action, ChannelAdminLogEventActionParticipantJoinByRequest):
        action_type = "join"
        payload["via_request"] = True
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif isinstance(action, ChannelAdminLogEventActionParticipantInvite):
        action_type = "invite"
        target_user = _participant_user(action)
    elif isinstance(action, ChannelAdminLogEventActionParticipantToggleBan):
        banned = bool(getattr(action, "new_banned_rights", None))
        action_type = "ban" if banned else "unban"
        target_user = _participant_user(action)
        payload["banned"] = banned
    elif isinstance(action, ChannelAdminLogEventActionParticipantToggleAdmin):
        admin_rights = getattr(action, "new_admin_rights", None)
        action_type = "promote" if admin_rights else "demote"
        target_user = _participant_user(action)
    elif isinstance(action, ChannelAdminLogEventActionEditMessage):
        action_type = "edit"
        msg = getattr(action, "new_message", None) or getattr(action, "prev_message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif isinstance(action, ChannelAdminLogEventActionDeleteMessage):
        action_type = "delete"
        messages = getattr(action, "message", None) or []
        if not isinstance(messages, list):
            messages = [messages]
        payload["message_ids"] = [getattr(m, "id", None) for m in messages if m is not None]
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionUpdatePinned,
            ChannelAdminLogEventActionPinMessage,
        ),
    ):
        action_type = "pinned"
        msg = getattr(action, "message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionChangeTitle,
            ChannelAdminLogEventActionChangeAbout,
            ChannelAdminLogEventActionChangePhoto,
            ChannelAdminLogEventActionChangeUsername,
            ChannelAdminLogEventActionChangeLinkedChat,
            ChannelAdminLogEventActionChangeLocation,
            ChannelAdminLogEventActionChangeStickerSet,
        ),
    ):
        action_type = "info"
        if isinstance(action, ChannelAdminLogEventActionChangeTitle):
            payload["new_title"] = getattr(action, "title", None)
        if isinstance(action, ChannelAdminLogEventActionChangeAbout):
            payload["new_about"] = getattr(action, "about", None)
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionToggleInvites,
            ChannelAdminLogEventActionTogglePreHistoryHidden,
            ChannelAdminLogEventActionToggleSignatures,
            ChannelAdminLogEventActionToggleSlowMode,
            ChannelAdminLogEventActionDefaultBannedRights,
            ChannelAdminLogEventActionToggleNoForwards,
            ChannelAdminLogEventActionChangeHistoryTTL,
        ),
    ):
        action_type = "settings"
    elif isinstance(action, ChannelAdminLogEventActionSendMessage):
        action_type = "send"
        msg = getattr(action, "message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionStartGroupCall,
            ChannelAdminLogEventActionDiscardGroupCall,
            ChannelAdminLogEventActionParticipantMute,
            ChannelAdminLogEventActionParticipantUnmute,
            ChannelAdminLogEventActionParticipantVolume,
        ),
    ):
        action_type = "group_call"
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionToggleForum,
            ChannelAdminLogEventActionCreateTopic,
            ChannelAdminLogEventActionDeleteTopic,
        ),
    ):
        action_type = "forums"
    elif isinstance(
        action,
        (
            ChannelAdminLogEventActionExportedInviteDelete,
            ChannelAdminLogEventActionExportedInviteEdit,
            ChannelAdminLogEventActionExportedInviteRevoke,
            ChannelAdminLogEventActionStopPoll,
        ),
    ):
        action_type = "settings"
    else:
        payload["raw_action"] = type(action).__name__

    target_id, target_username, target_display = _user_display(target_user)
    if target_id is not None:
        payload["target_user_id"] = target_id
    if target_username:
        payload["target_username"] = target_username
    if target_display:
        payload["target_display_name"] = target_display

    if action_type == "kick":
        pass
    elif action_type == "ban" and payload.get("banned") is False:
        action_type = "unban"

    return action_type, payload, target_id, target_username, target_display


def format_event_line(event: Any) -> str:
    """Format AdminLogEventRow or compatible object as HTML line."""
    from app.db import AdminLogEventRow

    if isinstance(event, AdminLogEventRow):
        action_type = event.action_type
        payload = event.action_payload
        event_date = event.event_date
        actor_username = event.actor_username
        actor_display = event.actor_display_name
    else:
        action_type = event.action_type
        payload = event.action_payload
        event_date = event.event_date
        actor_username = event.actor_username
        actor_display = event.actor_display_name

    dt_str = event_date.strftime("%d.%m.%Y %H:%M")
    label = ACTION_LABELS.get(action_type, action_type)

    target_username = payload.get("target_username")
    target_display = payload.get("target_display_name")
    target_id = payload.get("target_user_id")

    subject = _format_user_ref(target_username, target_display, target_id)
    actor = _format_user_ref(actor_username, actor_display, payload.get("actor_user_id"))

    if action_type in {"join", "leave", "invite", "ban", "unban", "kick", "promote", "demote"}:
        if subject:
            text = f"{subject} — {label}"
        else:
            text = label
        if actor and action_type in {"invite", "ban", "unban", "kick", "promote", "demote"}:
            text = f"{actor} → {text}"
    elif action_type in {"edit", "delete", "pinned", "send"}:
        msg_id = payload.get("message_id") or (payload.get("message_ids") or [None])[0]
        msg_part = f" (msg #{msg_id})" if msg_id else ""
        text = f"{label}{msg_part}"
        if actor:
            text = f"{actor}: {text}"
    else:
        text = label
        if actor:
            text = f"{actor}: {text}"

    return f"<code>{dt_str}</code> {text}"


def _format_user_ref(
    username: str | None,
    display: str | None,
    user_id: int | None,
) -> str | None:
    if username:
        return f"@{username}"
    if display:
        return display
    if user_id:
        return f"id{user_id}"
    return None


def format_events_message(events: list[Any], *, title: str) -> str:
    if not events:
        return f"<b>{title}</b>\n\nСобытий не найдено."
    lines = [format_event_line(e) for e in events]
    body = "\n".join(lines)
    if len(body) > 3500:
        body = body[:3500] + "\n…"
    return f"<b>{title}</b>\n\n{body}"


def format_stats(stats: dict[str, Any]) -> str:
    total = stats.get("total", 0)
    today = stats.get("today") or {}
    week = stats.get("week") or {}

    def _section(title: str, data: dict[str, int]) -> str:
        if not data:
            return f"<b>{title}</b>\n— нет событий"
        lines = []
        for action_type, cnt in sorted(data.items(), key=lambda x: -x[1]):
            label = ACTION_LABELS.get(action_type, action_type)
            lines.append(f"• {label}: {cnt}")
        return f"<b>{title}</b>\n" + "\n".join(lines)

    return (
        f"<b>Статистика «Недавних действий»</b>\n\n"
        f"Всего в базе: {total}\n\n"
        f"{_section('Сегодня', today)}\n\n"
        f"{_section('За 7 дней', week)}"
    )
