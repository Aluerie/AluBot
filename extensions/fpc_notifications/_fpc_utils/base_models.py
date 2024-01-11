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
        embed_image_url = embed.image.url
        colour = embed.colour
        if not embed_image_url:
            # todo: ???
            raise SomethingWentWrong("embed.image.url is None in FPC Notifications")
        if not colour:
            # todo: ???
            raise SomethingWentWrong("`embed.colour` is None in FPC Notifications")

        old_filename = embed_image_url.split("/")[-1].split(".png")[0]  # regex-less solution, lol
        new_filename = f"edited-{old_filename}.png"

        new_image = await self.edit_notification_image(embed_image_url, colour, bot)
        image_file = bot.transposer.image_to_file(new_image, filename=new_filename)
        embed.set_image(url=f"attachment://{image_file.filename}")
        try:
            await message.edit(embed=embed, attachments=[image_file])
        except discord.Forbidden:
            return
