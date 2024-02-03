from __future__ import annotations

import logging

# ruff: noqa: N818

log = logging.getLogger(__name__)

__all__: tuple[str, ...] = (
    "AluBotError",
    "BadArgument",
    "SomethingWentWrong",
    "UserError",
    "ErroneousUsage",
    "SilentError",
    "ResponseNotOK",
)


# this should inherit at least Exception so `except Exception as e` in discord.py don't fail
# maybe we will consider inheriting discord.DiscordException
class AluBotError(Exception):  # discord.DiscordException):
    """The base exception for AluBot. All other exceptions should inherit from this."""

    __slots__: tuple[str, ...] = ()


class BadArgument(AluBotError):
    """My own BadArgument exception.
    Analogy to commands.BadArgument but raised by my own conversions and conditions
    """

    __slots__: tuple[str, ...] = ()


class SomethingWentWrong(AluBotError):
    """When something goes wrong and I want to notify the user about it."""

    __slots__: tuple[str, ...] = ()


class UserError(AluBotError):
    """user made a mistake and I want to notify them about it."""

    __slots__: tuple[str, ...] = ()


class ErroneousUsage(AluBotError):
    """This exception does not mean an error happened. But rather some bad command usage.

    Example, somebody uses `/text-to-speech stop` while the bot is not even in a voice chat.
    Well - it's not a real exception, but rather a bad usage, which is given in the command itself.
    The reason it's exception in the first place so error handler handles it properly as in embed/ephemeral/etc.

    We don't set_author in error_handler for this one.
    """

    __slots__: tuple[str, ...] = ()


class SilentError(AluBotError):
    """Error that will be specifically ignored by command handlers."""

    __slots__: tuple[str, ...] = ()


class ResponseNotOK(AluBotError):
    """Raised we aiohttp session response is not OK

    Sometimes we just specifically need to raise an error in those cases
    when response from `self.bot.session.get(url)` is not OK.
    I.e. Cache Updates.
    """

    __slots__: tuple[str, ...] = ()
