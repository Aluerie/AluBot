from __future__ import annotations

import abc
import logging
import re
from typing import TYPE_CHECKING, Any, Optional, Self, TypedDict

import discord

from utils import errors

from . import FPCCog

if TYPE_CHECKING:
    from PIL import Image

    from bot import AluBot


__all__ = (
    "BaseMatchToSend",
    "BaseMatchToEdit",
)


class BaseMatchToSend(abc.ABC):
    if TYPE_CHECKING:
        status: str

    def __init__(self, bot: AluBot) -> None:
        self.bot: AluBot = bot

    @abc.abstractmethod
    async def notification_image(self) -> Image.Image:
        """Get notification image that will be `set_image` into embed."""

    @abc.abstractmethod
    async def insert_into_game_messages(self, message_id: int, channel_id: int) -> None:
        """Insert the match to messages table so we can edit it later"""

    @abc.abstractmethod
    async def embed_and_file(self) -> tuple[discord.Embed, discord.File]:
        """Get embed and file"""


class BaseMatchToEdit(abc.ABC):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @abc.abstractmethod
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        """Edit the notification image."""
