from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict

import discord

from utils import errors

from . import FPCCog

if TYPE_CHECKING:
    from bot import AluBot

    from ._models import BaseMatchToEdit, BaseMatchToSend

    class GetTwitchLivePlayerRow(TypedDict):
        twitch_id: int
        player_id: int

    class ChannelSpoilQueryRow(TypedDict):
        channel_id: int
        spoil: bool


__all__ = ("BaseNotifications",)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class BaseNotifications(FPCCog):
    def __init__(self, bot: AluBot, prefix: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.prefix: str = prefix

        self.message_cache: dict[int, discord.Message] = {}

    async def get_twitch_live_player_ids(self, twitch_category_id: str, player_ids: list[int]) -> list[int]:
        """Get `player_id` for favourite FPC streams that are currently live on Twitch."""
        query = f"""
            SELECT twitch_id, player_id
            FROM {self.prefix}_players
            WHERE player_id=ANY($1)
        """
        rows: list[GetTwitchLivePlayerRow] = await self.bot.pool.fetch(query, player_ids)
        twitch_id_to_player_id = {row["twitch_id"]: row["player_id"] for row in rows}
        if not twitch_id_to_player_id:
            # otherwise fetch_streams fetches top100 streams and we dont want that.
            return []

        live_player_ids = [
            twitch_id_to_player_id[stream.user.id]
            for stream in await self.bot.twitch.fetch_streams(user_ids=list(twitch_id_to_player_id.keys()))
            if stream.game_id == twitch_category_id  # type: ignore # stream.game_id is actually str, not int.
        ]
        return live_player_ids

    async def send_match(self, match: BaseMatchToSend, channel_spoil_tuples: list[tuple[int, bool]]) -> None:
        embed, image_file = await match.embed_and_file()

        for channel_id, spoil in channel_spoil_tuples:
            try:
                channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            except discord.NotFound:
                # apparently this error sometimes randomly triggers
                # for even known channels that "should" be in cache
                # todo: idk how to approach this NotFound problem
                raise

            assert isinstance(channel, discord.TextChannel)
            try:
                message = await channel.send(embed=embed, file=image_file)
            except Exception as exc:
                raise exc
            else:
                if spoil:
                    self.message_cache[message.id] = message
                    await match.insert_into_game_messages(message.id, channel.id)

    async def edit_match(self, match: BaseMatchToEdit, channel_message_tuples: list[tuple[int, int]]) -> None:
        new_image_file: discord.File | None = None

        for channel_id, message_id in channel_message_tuples:
            try:
                # try to find in cache
                message = self.message_cache[message_id]
            except KeyError:
                # we have to fetch it
                try:
                    channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    # apparently this error sometimes randomly triggers
                    # for even known channels that "should" be in cache
                    # todo: idk how to approach this NotFound problem
                    raise

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
                    msg = "embed.image.url is None in FPC Notifications"
                    raise errors.SomethingWentWrong(msg)
                if not colour:
                    msg = "`embed.colour` is None in FPC Notifications"
                    raise errors.SomethingWentWrong(msg)

                old_filename = embed_image_url.split("/")[-1].split(".png")[0]  # regex-less solution, lol

                new_filename = f"edited-{old_filename}.png"
                log.debug(new_filename)
                new_image = await match.edit_notification_image(embed_image_url, colour)

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
            else:
                self.message_cache.pop(message.id, None)
