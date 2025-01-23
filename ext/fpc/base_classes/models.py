from __future__ import annotations

import abc
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    import discord
    from PIL import Image

    from bot import AluBot


__all__ = (
    "BaseMatchToEdit",
    "BaseMatchToSend",
    "RecipientKwargs",
)


class RecipientKwargs(TypedDict):
    embed: discord.Embed
    file: discord.File
    username: NotRequired[str]
    avatar_url: NotRequired[str]


class BaseMatchToSend(abc.ABC):
    if TYPE_CHECKING:
        status: str

    def __init__(
        self,
        bot: AluBot,
        # player_name: str,
        # character_name: str,
        # preview_url: str,
    ) -> None:
        self.bot: AluBot = bot
        # self.player_name: str = player_name
        # self.character_name: str = character_name
        # self.preview_url: str = preview_url

    @abc.abstractmethod
    async def notification_image(self) -> Image.Image:
        """Get notification image that will be `set_image` into embed."""

    @abc.abstractmethod
    async def insert_into_game_messages(self, message_id: int, channel_id: int) -> None:
        """Insert the match to messages table so we can edit it later."""

    @abc.abstractmethod
    async def webhook_send_kwargs(self) -> RecipientKwargs:
        """Get embed and file."""
        # image = await self.notification_image()

        # title = f"{self.player_name} - {self.character_name}"
        # filename = twitch_data["twitch_status"] + "-" + re.sub(r"[_' ]", "", title) + ".png"


class BaseMatchToEdit(abc.ABC):
    def __init__(self, bot: AluBot) -> None:
        self.bot: AluBot = bot

    @abc.abstractmethod
    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        """Edit the notification image."""
