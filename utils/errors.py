"""CUSTOM ERRORS.

This file is basically a list of custom errors that I raise elsewhere in the code.
The rule of thumb: If I write my own `raise` then it should raise an error from this list.

The reason these errors are gathered together is so `ctx_cmd_errors.py` and such don't have to
import half of the bot folders (i.e. translation error would always mean translator-package been imported)
"""

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
    "PlaceholderRaiseError",
    "PermissionsError",
)


# this should inherit at least Exception so `except Exception as e` in discord.py don't fail
# maybe we will consider inheriting discord.DiscordException
class AluBotError(Exception):  # discord.DiscordException):
    """The base exception for AluBot. All other exceptions should inherit from this."""

    __slots__: tuple[str, ...] = ()


class BadArgument(AluBotError):
    """My own BadArgument exception.

    Analogy to `commands.BadArgument` but raised by my own conversions and conditions.
    """

    __slots__: tuple[str, ...] = ()


class SomethingWentWrong(AluBotError):
    """When something goes wrong."""

    __slots__: tuple[str, ...] = ()


class UserError(AluBotError):
    """User made a mistake."""

    __slots__: tuple[str, ...] = ()


class ErroneousUsage(AluBotError):
    """Erroneous usage of the bot features.

    This exception does not mean an error in the bot happened. Or that it's a user mistake.
    But instead, user didn't use the bot features correctly.

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
    """Raised when `aiohttp`'s session response is not OK.

    Sometimes we just specifically need to raise an error in those cases
    when response from `self.bot.session.get(url)` is not OK.
    I.e. Cache Updates.
    """

    __slots__: tuple[str, ...] = ()


class TranslateError(AluBotError):
    """Raised when there is an error in translate functionality."""

    def __init__(self, status_code: int, text: str) -> None:
        self.status_code: int = status_code
        self.text: str = text
        super().__init__(f"Google Translate responded with HTTP Status Code {status_code}")


class PlaceholderRaiseError(AluBotError):
    """Placeholder Error.

    Maybe silly thing, but instead of doing empty `raise` that is not clear later in logs what exactly it is
    I prefer raising my own placeholder error with a message.
    This is usually used in a code where I'm unsure what to do and how else to handle the situation.
    """

    __slots__: tuple[str, ...] = ()


class TimeoutError(AluBotError):
    __slots__: tuple[str, ...] = ()


class PermissionsError(AluBotError):
    __slots__: tuple[str, ...] = ()
