from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord

from utils import SomethingWentWrong

if TYPE_CHECKING:
    from PIL import Image

    from bot import AluBot

__all__ = ("BasePostMatchPlayer",)


class BasePostMatchPlayer:
    def __init__(
        self,
        *,
        channel_id: int,
        message_id: int,
    ):
        self.channel_id = channel_id
        self.message_id = message_id

    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour, bot: AluBot) -> Image.Image:
        raise NotImplementedError

    async def edit_notification_embed(self, bot: AluBot) -> None:
        channel: Optional[discord.TextChannel] = bot.get_channel(self.channel_id)  # type:ignore
        if channel is None:
            # todo: ???
            return

        try:
            message = await channel.fetch_message(self.message_id)
        except discord.NotFound:
            return

        embed = message.embeds[0]
        embed_image_url = embed.image.proxy_url
        colour = embed.colour
        if not embed_image_url:
            # todo: ???
            raise SomethingWentWrong("embed.image.proxy_url is None in FPC Notifications")
        if not colour:
            # todo: ???
            raise SomethingWentWrong("`embed.colour` is None in FPC Notifications")

        filename = embed_image_url.split("/")[-1]
        image_file = bot.transposer.image_to_file(
            await self.edit_notification_image(embed_image_url, colour, bot),
            filename=f"edited-{filename}.png",
        )
        embed.set_image(url=f"attachment://{image_file.filename}")
        try:
            await message.edit(embed=embed, attachments=[image_file])
        except discord.Forbidden:
            return
