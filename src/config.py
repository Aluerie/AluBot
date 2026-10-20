"""Config.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("env",)


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )


class Env(EnvConfig):
    PROJECT_NAME: str
    DISCORD_TOKEN_ALUBOT: str
    DISCORD_TOKEN_YENBOT: str
    POSTGRES_PROD: str
    POSTGRES_TEST: str
    WEBHOOK_LOGGER: str
    WEBHOOK_DOTANEWS: str
    WEBHOOK_ALU_ERROR: str
    WEBHOOK_ALU_NOTIFICATION: str
    WEBHOOK_YEN_ERROR: str
    WEBHOOK_YEN_NOTIFICATION: str
    PING_PROD_MENTION: str
    PING_TEST_MENTION: str
    WOLFRAM_TOKEN: str
    GIT_PERSONAL_TOKEN: str


env = Env()
