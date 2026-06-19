from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_int_list(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, int):
        return (value,)
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value).split(",")
    result: list[int] = []
    for item in items:
        s = str(item).strip()
        if not s:
            continue
        try:
            result.append(int(s))
        except ValueError:
            continue
    return tuple(result)


def _parse_str_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value).split(",")
    return tuple(s.strip().lower() for s in items if str(s).strip())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    telegram_api_id: int = Field(alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(alias="TELEGRAM_API_HASH")
    telegram_session: str = Field(alias="TELEGRAM_SESSION")

    channel_username: str = Field(alias="CHANNEL_USERNAME")

    # Строки из .env — pydantic-settings не умеет tuple через запятую без JSON.
    admin_ids_env: str = Field(default="", alias="ADMIN_IDS")
    admin_notify_ids_env: str = Field(default="", alias="ADMIN_NOTIFY_IDS")
    notify_event_types_env: str = Field(
        default="join,leave,ban,kick,unban",
        alias="NOTIFY_EVENT_TYPES",
    )

    poll_interval_seconds: int = Field(default=30, alias="POLL_INTERVAL_SECONDS")
    initial_backfill_limit: int = Field(default=500, alias="INITIAL_BACKFILL_LIMIT")
    database_path: str = Field(default="data/bot.db", alias="DATABASE_PATH")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_ids(self) -> tuple[int, ...]:
        return _parse_int_list(self.admin_ids_env)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def admin_notify_ids(self) -> tuple[int, ...]:
        return _parse_int_list(self.admin_notify_ids_env)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def notify_event_types(self) -> tuple[str, ...]:
        return _parse_str_list(self.notify_event_types_env)

    @field_validator("channel_username")
    @classmethod
    def _normalize_channel(cls, value: str) -> str:
        s = value.strip()
        if not s:
            raise ValueError("CHANNEL_USERNAME is required")
        if not s.startswith("@"):
            s = f"@{s}"
        return s

    def effective_notify_ids(self) -> tuple[int, ...]:
        return self.admin_notify_ids or self.admin_ids


settings = Settings()
