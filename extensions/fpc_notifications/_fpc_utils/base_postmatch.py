from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord

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

    async def edit_notification_image(self, attachment: discord.Attachment, bot: AluBot) -> Image.Image:
        raise NotImplementedError

    async def edit_notification_embed(self, bot: AluBot) -> None:
        ch: Optional[discord.TextChannel] = bot.get_channel(self.channel_id)  # type:ignore
        if ch is None:
            # todo: ???
            return

        try:
            message = await ch.fetch_message(self.message_id)
        except discord.NotFound:
            return

        embed = message.embeds[0]
        attachment = message.attachments[0]

        image_file = bot.transposer.image_to_file(
            await self.edit_notification_image(attachment, bot),
            filename=f"edited-{attachment.filename}.png",
        )
        embed.set_image(url=f"attachment://{image_file.filename}")
        try:
            await message.edit(embed=embed, attachments=[image_file])
        except discord.Forbidden:
            return
