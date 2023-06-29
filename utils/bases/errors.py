from __future__ import annotations

import logging
from typing import Tuple

import discord

log = logging.getLogger(__name__)

__all__: Tuple[str, ...] = ('AluBotException', 'SomethingWentWrong', 'UserError')


class AluBotException(discord.ClientException):
    """The base exception for AluBot. All other exceptions should inherit from this."""

    __slots__: Tuple[str, ...] = ()


class BadArgument(AluBotException):
    """My own BadArgument exception.
    Analogy to commands.BadArgument but raised by my own conversions and conditions
    """

    __slots__: Tuple[str, ...] = ()


class SomethingWentWrong(AluBotException):
    """When something goes wrong and I want to notify the user about it."""

    __slots__: Tuple[str, ...] = ()


class UserError(AluBotException):
    """user made a mistake and I want to notify them about it."""

    __slots__: Tuple[str, ...] = ()


class ErroneousUsage(AluBotException):
    """This exception does not mean an error happened. But rather some bad command usage.

    Example, somebody uses `/text-to-speech stop` while the bot is not even in a voice chat.
    Well - it's not a real exception, but rather a bad usage, which is given in the command itself.
    The reason it's exception in the first place so error handler handles it properly as in embed/ephemeral/etc.

    We don't set_author in error_handler for this one."""

    __slots__: Tuple[str, ...] = ()
