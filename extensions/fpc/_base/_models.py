from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING, Any, Optional, TypedDict

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
    async def get_embed_and_file(self) -> tuple[discord.Embed, discord.File]:
        """Get embed and file"""

    @abc.abstractmethod
    async def insert_into_game_messages(self, message_id: int, channel_id: int) -> None:
        """Insert the match to messages table so we can edit it later"""


class BaseMatchToEdit(abc.ABC):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @abc.abstractmethod
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        """Edit"""
