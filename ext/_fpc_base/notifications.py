from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

import discord

from bot import AluCog
from utils import errors, mimics

if TYPE_CHECKING:
    from bot import AluBot

    from .models import BaseMatchToEdit, BaseMatchToSend

    class GetTwitchLivePlayerRow(TypedDict):
        twitch_id: str
        player_id: int

    class ChannelSpoilQueryRow(TypedDict):
        channel_id: int
        spoil: bool

    import twitchio

__all__ = (
    "BaseNotifications",
    "EditTuple",
    "RecipientTuple",
)


class RecipientTuple(NamedTuple):
    channel_id: int
    spoil: bool


class EditTuple(NamedTuple):
    channel_id: int
    message_id: int


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class BaseNotifications(AluCog):
    def __init__(self, bot: AluBot, prefix: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.prefix: str = prefix

        self.message_cache: dict[int, discord.WebhookMessage] = {}

    async def get_player_streams(self, twitch_category_id: str, player_ids: list[int]) -> dict[int, twitchio.Stream]:
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
            return {}

        return {
            twitch_id_to_player_id[stream.user.id]: stream
            for stream in await self.bot.twitch.fetch_streams(user_ids=list(twitch_id_to_player_id.keys()))
            if stream.game_id == twitch_category_id
        }

    async def send_match(self, match: BaseMatchToSend, recipients: list[RecipientTuple]) -> None:
        send_kwargs = await match.webhook_send_kwargs()

        for recipient in recipients:
            channel = self.bot.get_channel(recipient.channel_id) or await self.bot.fetch_channel(recipient.channel_id)

            assert isinstance(channel, discord.TextChannel)
            mimic = mimics.Mimic.from_channel(self.bot, channel)
            message = await mimic.send(wait=True, report=True, **send_kwargs)
            if recipient.spoil:
                self.message_cache[message.id] = message
                await match.insert_into_game_messages(message.id, channel.id)

    async def edit_match(self, match: BaseMatchToEdit, edits: list[EditTuple]) -> None:
        new_image_file: discord.File | None = None

        for edit in edits:
            try:
                # try to find in cache
                message = self.message_cache[edit.message_id]
            except KeyError:
                # we have to fetch it
                webhook = await self.bot.webhook_from_database(edit.channel_id)
                message = await webhook.fetch_message(edit.message_id)

            embed = message.embeds[0]
            if new_image_file is None:
                embed_image_url = embed.image.url
                color = embed.color
                if not embed_image_url:
                    msg = "embed.image.url is None in FPC Notifications"
                    raise errors.SomethingWentWrong(msg)
                if not color:
                    msg = "`embed.color` is None in FPC Notifications"
                    raise errors.SomethingWentWrong(msg)

                old_filename = embed_image_url.split("/")[-1].split(".png")[0]  # regex-less solution, lol

                new_filename = f"edited-{old_filename}.png"
                log.debug(new_filename)
                new_image = await match.edit_notification_image(embed_image_url, color)

                new_image_file = self.bot.transposer.image_to_file(new_image, filename=new_filename)
            else:
                # already have the file object from some other channel message editing
                # since the image should be same everywhere
                pass

            embed.set_image(url=f"attachment://{new_image_file.filename}")
            await message.edit(embed=embed, attachments=[new_image_file])
            self.message_cache.pop(message.id, None)
