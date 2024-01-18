from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord

from utils import errors

if TYPE_CHECKING:
    from PIL import Image

    from bot import AluBot

__all__ = ("BasePostMatchPlayer",)


class BasePostMatchPlayer:
    def __init__(
        self,
        bot: AluBot,
        *,
        channel_message_tuples: list[tuple[int, int]],
    ):
        self.bot: AluBot = bot
        self.channel_message_tuples: list[tuple[int, int]] = channel_message_tuples

    async def edit_notification_image(self, embed_image_url: str, colour: discord.Colour) -> Image.Image:
        raise NotImplementedError

    async def edit_notification_embed(self) -> None:
        new_image_file: Optional[discord.File] = None

        for channel_id, message_id in self.channel_message_tuples:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            if channel is None:
                raise errors.SomethingWentWrong("Channel is None in FPC Notifications")

            assert isinstance(channel, discord.TextChannel)

            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                raise

            embed = message.embeds[0]
            if new_image_file is None:
                embed_image_url = embed.image.url
                colour = embed.colour
                if not embed_image_url:
                    raise errors.SomethingWentWrong("embed.image.url is None in FPC Notifications")
                if not colour:
                    raise errors.SomethingWentWrong("`embed.colour` is None in FPC Notifications")

                old_filename = embed_image_url.split("/")[-1].split(".png")[0]  # regex-less solution, lol

                new_filename = f"edited-{old_filename}.png"
                new_image = await self.edit_notification_image(embed_image_url, colour)

                new_image_file = self.bot.transposer.image_to_file(new_image, filename=new_filename)
            else:
                # already have the file object from some other channel message editing
                # since the image should be same everywhere
                pass

            embed.set_image(url=f"attachment://{new_image_file.filename}")
            try:
                await message.edit(embed=embed, attachments=[new_image_file])
            except discord.Forbidden:
                raise
