from typing import TypedDict

__all__ = ("Config",)


class Discord(TypedDict):
    ALUBOT: str
    YENBOT: str


class Postgres(TypedDict):
    VPS: str
    HOME: str


class SteamAccount(TypedDict):
    USERNAME: str
    PASSWORD: str


class Steam(TypedDict):
    ALUERIE_FRIEND_ID: int
    ALUBOT: SteamAccount
    YENBOT: SteamAccount


class Twitch(TypedDict):
    CLIENT_ID: str
    CLIENT_SECRET: str


class Webhooks(TypedDict):
    ERROR: str
    SPAM: str
    LOGGER: str
    DOTA_NEWS: str
    YEN_ERROR: str
    YEN_SPAM: str


class Tokens(TypedDict):
    STRATZ_BEARER: str
    WOLFRAM: str
    RIOT: str
    GIT_PERSONAL: str
    STEAM: str


class Config(TypedDict):
    """Type-hints for dictionary created from loading `config.toml` file."""

    DISCORD: Discord
    POSTGRES: Postgres
    STEAM: Steam
    TWITCH: Twitch
    WEBHOOKS: Webhooks
    TOKENS: Tokens
