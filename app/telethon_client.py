from __future__ import annotations

import logging
import os
from typing import Any

import socks
from telethon import TelegramClient
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

_PROXY_TYPES = {
    "socks5": socks.SOCKS5,
    "socks4": socks.SOCKS4,
    "http": socks.HTTP,
}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def parse_proxy_from_env() -> tuple[Any | None, type | None]:
    """Returns (proxy, connection_class). Both None if proxy is not configured."""
    proxy_type = _env("TELEGRAM_PROXY_TYPE").lower()
    host = _env("TELEGRAM_PROXY_HOST")
    port_raw = _env("TELEGRAM_PROXY_PORT")

    if not proxy_type or not host or not port_raw:
        return None, None

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"TELEGRAM_PROXY_PORT must be an integer, got {port_raw!r}") from exc

    username = _env("TELEGRAM_PROXY_USERNAME") or None
    password = _env("TELEGRAM_PROXY_PASSWORD") or None

    if proxy_type == "mtproxy":
        secret = _env("TELEGRAM_MTPROXY_SECRET")
        if not secret:
            raise ValueError("TELEGRAM_MTPROXY_SECRET is required for mtproxy")
        return ("mtproxy", host, port, secret), ConnectionTcpMTProxyRandomizedIntermediate

    socks_type = _PROXY_TYPES.get(proxy_type)
    if socks_type is None:
        allowed = ", ".join(sorted({* _PROXY_TYPES.keys(), "mtproxy"}))
        raise ValueError(
            f"Unsupported TELEGRAM_PROXY_TYPE={proxy_type!r}. Allowed: {allowed}"
        )

    if username or password:
        proxy: Any = (socks_type, host, port, True, username, password)
    else:
        proxy = (socks_type, host, port)

    return proxy, None


def connect_timeout_from_env(default: int = 30) -> int:
    raw = _env("TELEGRAM_CONNECT_TIMEOUT")
    if not raw:
        return default
    try:
        return max(5, int(raw))
    except ValueError:
        return default


def create_telegram_client(
    *,
    session: str | StringSession,
    api_id: int,
    api_hash: str,
) -> TelegramClient:
    proxy, connection_cls = parse_proxy_from_env()
    timeout = connect_timeout_from_env()

    kwargs: dict[str, Any] = {
        "timeout": timeout,
        "connection_retries": 5,
        "retry_delay": 2,
    }
    if proxy is not None:
        kwargs["proxy"] = proxy
        if connection_cls is not None:
            kwargs["connection"] = connection_cls
        logger.info(
            "Telethon proxy: type=%s host=%s port=%s",
            _env("TELEGRAM_PROXY_TYPE"),
            _env("TELEGRAM_PROXY_HOST"),
            _env("TELEGRAM_PROXY_PORT"),
        )
    else:
        logger.info("Telethon proxy: not configured (direct MTProto connection)")

    return TelegramClient(
        StringSession(session) if isinstance(session, str) else session,
        api_id,
        api_hash,
        **kwargs,
    )


def connection_help_text() -> str:
    return (
        "Telethon не смог подключиться к серверам Telegram (MTProto).\n\n"
        "Частая причина — блокировка MTProto в сети. Bot API (HTTPS) может работать,\n"
        "а Telethon — нет.\n\n"
        "Что сделать:\n"
        "1. Включите VPN или локальный прокси (часто SOCKS5 на 127.0.0.1:1080).\n"
        "2. Добавьте в .env, например:\n"
        "   TELEGRAM_PROXY_TYPE=socks5\n"
        "   TELEGRAM_PROXY_HOST=127.0.0.1\n"
        "   TELEGRAM_PROXY_PORT=1080\n"
        "3. Для MTProxy:\n"
        "   TELEGRAM_PROXY_TYPE=mtproxy\n"
        "   TELEGRAM_PROXY_HOST=proxy.example.com\n"
        "   TELEGRAM_PROXY_PORT=443\n"
        "   TELEGRAM_MTPROXY_SECRET=...\n"
        "4. Увеличьте таймаут: TELEGRAM_CONNECT_TIMEOUT=60\n"
    )
