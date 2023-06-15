from __future__ import annotations

import logging
from typing import Tuple

import discord

log = logging.getLogger(__name__)

__all__: Tuple[str, ...] = (
    'AluBotException',
    'SomethingWentWrong',
    'UserError'
)


class AluBotException(discord.ClientException):
    """The base exception for AluBot. All other exceptions should inherit from this."""

    __slots__: Tuple[str, ...] = ()


class SomethingWentWrong(AluBotException):
    """When something goes wrong and I want to notify the user about it."""

    __slots__: Tuple[str, ...] = ()


class UserError(AluBotException):
    """user made a mistake and I want to notify them about it."""

    __slots__: Tuple[str, ...] = ()

