from __future__ import annotations

from typing import Any

from telethon.tl.types import User

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

_JOIN_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionParticipantJoin",
        "ChannelAdminLogEventActionParticipantJoinByInvite",
        "ChannelAdminLogEventActionParticipantJoinByRequest",
    }
)
_LEAVE_ACTIONS = frozenset({"ChannelAdminLogEventActionParticipantLeave"})
_PINNED_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionUpdatePinned",
        "ChannelAdminLogEventActionPinMessage",
        "ChannelAdminLogEventActionPinTopic",
    }
)
_INFO_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionChangeTitle",
        "ChannelAdminLogEventActionChangeAbout",
        "ChannelAdminLogEventActionChangePhoto",
        "ChannelAdminLogEventActionChangeUsername",
        "ChannelAdminLogEventActionChangeUsernames",
        "ChannelAdminLogEventActionChangeLinkedChat",
        "ChannelAdminLogEventActionChangeLocation",
        "ChannelAdminLogEventActionChangeStickerSet",
        "ChannelAdminLogEventActionChangeEmojiStickerSet",
        "ChannelAdminLogEventActionChangeWallpaper",
        "ChannelAdminLogEventActionChangePeerColor",
        "ChannelAdminLogEventActionChangeProfilePeerColor",
        "ChannelAdminLogEventActionChangeEmojiStatus",
    }
)
_SETTINGS_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionToggleInvites",
        "ChannelAdminLogEventActionTogglePreHistoryHidden",
        "ChannelAdminLogEventActionToggleSignatures",
        "ChannelAdminLogEventActionToggleSignatureProfiles",
        "ChannelAdminLogEventActionToggleSlowMode",
        "ChannelAdminLogEventActionDefaultBannedRights",
        "ChannelAdminLogEventActionToggleNoForwards",
        "ChannelAdminLogEventActionChangeHistoryTTL",
        "ChannelAdminLogEventActionExportedInviteDelete",
        "ChannelAdminLogEventActionExportedInviteEdit",
        "ChannelAdminLogEventActionExportedInviteRevoke",
        "ChannelAdminLogEventActionStopPoll",
        "ChannelAdminLogEventActionToggleAntiSpam",
        "ChannelAdminLogEventActionToggleGroupCallSetting",
        "ChannelAdminLogEventActionChangeAvailableReactions",
    }
)
_GROUP_CALL_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionStartGroupCall",
        "ChannelAdminLogEventActionDiscardGroupCall",
        "ChannelAdminLogEventActionParticipantMute",
        "ChannelAdminLogEventActionParticipantUnmute",
        "ChannelAdminLogEventActionParticipantVolume",
    }
)
_FORUM_ACTIONS = frozenset(
    {
        "ChannelAdminLogEventActionToggleForum",
        "ChannelAdminLogEventActionCreateTopic",
        "ChannelAdminLogEventActionDeleteTopic",
        "ChannelAdminLogEventActionEditTopic",
    }
)


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


def _action_class_name(action: Any) -> str:
    return type(action).__name__


def parse_admin_log_event(event: Any) -> tuple[str, dict[str, Any], int | None, str | None, str | None]:
    """Returns action_type, payload, target_user_id, target_username, target_display_name."""
    action = event.action
    class_name = _action_class_name(action)
    payload: dict[str, Any] = {"raw_action": class_name}

    actor_id, actor_username, actor_display = _user_display(getattr(event, "user", None))
    if actor_id is not None:
        payload["actor_user_id"] = actor_id
    if actor_username:
        payload["actor_username"] = actor_username
    if actor_display:
        payload["actor_display_name"] = actor_display

    target_user: User | None = None
    action_type = "other"

    if class_name in _JOIN_ACTIONS:
        action_type = "join"
        if class_name == "ChannelAdminLogEventActionParticipantJoinByInvite":
            payload["via_invite"] = True
        if class_name == "ChannelAdminLogEventActionParticipantJoinByRequest":
            payload["via_request"] = True
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif class_name in _LEAVE_ACTIONS:
        action_type = "leave"
        target_user = _participant_user(action) or getattr(event, "user", None)
    elif class_name == "ChannelAdminLogEventActionParticipantInvite":
        action_type = "invite"
        target_user = _participant_user(action)
    elif class_name == "ChannelAdminLogEventActionParticipantToggleBan":
        banned = bool(getattr(action, "new_banned_rights", None))
        action_type = "ban" if banned else "unban"
        target_user = _participant_user(action)
        payload["banned"] = banned
    elif class_name == "ChannelAdminLogEventActionParticipantToggleAdmin":
        admin_rights = getattr(action, "new_admin_rights", None)
        action_type = "promote" if admin_rights else "demote"
        target_user = _participant_user(action)
    elif class_name == "ChannelAdminLogEventActionEditMessage":
        action_type = "edit"
        msg = getattr(action, "new_message", None) or getattr(action, "prev_message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif class_name == "ChannelAdminLogEventActionDeleteMessage":
        action_type = "delete"
        messages = getattr(action, "message", None) or []
        if not isinstance(messages, list):
            messages = [messages]
        payload["message_ids"] = [getattr(m, "id", None) for m in messages if m is not None]
    elif class_name in _PINNED_ACTIONS:
        action_type = "pinned"
        msg = getattr(action, "message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif class_name in _INFO_ACTIONS:
        action_type = "info"
        if class_name == "ChannelAdminLogEventActionChangeTitle":
            payload["new_title"] = getattr(action, "title", None)
        if class_name == "ChannelAdminLogEventActionChangeAbout":
            payload["new_about"] = getattr(action, "about", None)
    elif class_name in _SETTINGS_ACTIONS:
        action_type = "settings"
    elif class_name == "ChannelAdminLogEventActionSendMessage":
        action_type = "send"
        msg = getattr(action, "message", None)
        if msg is not None:
            payload["message_id"] = getattr(msg, "id", None)
    elif class_name in _GROUP_CALL_ACTIONS:
        action_type = "group_call"
    elif class_name in _FORUM_ACTIONS:
        action_type = "forums"
    elif class_name == "ChannelAdminLogEventActionParticipantSubExtend":
        action_type = "join"
        target_user = _participant_user(action) or getattr(event, "user", None)

    target_id, target_username, target_display = _user_display(target_user)
    if target_id is not None:
        payload["target_user_id"] = target_id
    if target_username:
        payload["target_username"] = target_username
    if target_display:
        payload["target_display_name"] = target_display

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
