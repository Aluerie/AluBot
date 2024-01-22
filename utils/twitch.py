from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional, TypedDict, override

import discord
import twitchio
from discord.ext.commands import BadArgument
from twitchio.ext import eventsub

import config

from . import const, errors, formats

if TYPE_CHECKING:
    from bot import AluBot

    class StreamData(TypedDict):
        display_name: str
        name: str
        url: str
        logo_url: str
        online: bool
        game: str
        title: str
        preview_url: str


log = logging.getLogger(__name__)


class TwitchClient(twitchio.Client):
    def __init__(self, bot: AluBot):
        super().__init__(token=config.TWITCH_ACCESS_TOKEN)

        self.discord_bot: AluBot = bot
        self.eventsub: eventsub.EventSubWSClient = eventsub.EventSubWSClient(self)

    # EVENT SUB ########################################################################################################

    async def event_eventsub_notification(self, event: eventsub.NotificationEvent) -> None:
        if isinstance(event.data, eventsub.StreamOnlineData):
            self.discord_bot.dispatch("twitchio_stream_start", event.data)

        # testing with channel points
        elif isinstance(event.data, eventsub.CustomRewardRedemptionAddUpdateData):
            self.discord_bot.dispatch("twitchio_channel_points_redeem", event.data)

    # OVERRIDE #########################################################################################################

    @override
    async def event_error(self, error: Exception, data: Optional[str] = None):
        embed = discord.Embed(colour=const.Colour.twitch(), title="Twitch Client Error")
        if data:
            embed.description = data[2048:]
        await self.discord_bot.exc_manager.register_error(error, source=embed, where="Twitch Client")

    # UTILITIES ########################################################################################################

    async def get_twitch_user(self, user_name: str) -> twitchio.User:
        """Get twitch_id by user_login"""
        user = next(iter(await self.fetch_users(names=[user_name])), None)
        if not user:
            raise errors.BadArgument(
                f"Error checking stream with name `{user_name}`.\n User either does not exist or is banned."
            )

        return user

    async def name_by_twitch_id(self, user_id: int) -> str:
        """Get display_name by twitch_id"""
        user = next(iter(await self.fetch_users(ids=[user_id])), None)
        if not user:
            raise errors.BadArgument(
                f"Error checking stream with id `{user_id}`.\n User either does not exist or is banned."
            )

        return user.display_name

    async def last_vod_link(self, user_id: int, seconds_ago: int = 0, markdown: bool = True) -> str:
        """Get last vod link for user with `user_id` with timestamp as well"""
        video: twitchio.Video | None = next(iter(await self.fetch_videos(user_id=user_id, period="day")), None)
        if not video:
            return ""

        def get_time_from_hms(hms_time: str):
            """Convert time after `?t=` in vod link into amount of seconds

            03h51m08s -> 3 * 3600 + 51 * 60 + 8 = 13868
            """

            def regex_time(letter: str) -> int:
                """regex_time('h') = 3, regex_time('m') = 51, regex_time('s') = 8 for above example"""
                pattern = r"\d+(?={})".format(letter)
                units = re.search(pattern, hms_time)
                return int(units.group(0)) if units else 0

            timeunit_dict = {"h": 3600, "m": 60, "s": 1}
            return sum([v * regex_time(letter) for letter, v in timeunit_dict.items()])

        duration = get_time_from_hms(video.duration)
        vod_url = f"{video.url}?t={formats.human_timedelta(duration - seconds_ago, strip=True, suffix=False)}"
        return f"/[VOD]({vod_url})" if markdown else vod_url

    async def get_twitch_stream(self, twitch_id: int) -> TwitchStream:
        user = next(iter(await self.fetch_users(ids=[twitch_id])))
        stream = next(iter(await self.fetch_streams(user_ids=[twitch_id])), None)  # None if offline
        return TwitchStream(twitch_id, user, stream)


class TwitchStream:
    """My own helping class that unites twitchio.User and twitch.Stream together

    and has needed attributes, i.e. since offline users don't have `.game` data
    we fill it ourselves.
    """

    def __init__(self, twitch_id: int, user: twitchio.User, stream: Optional[twitchio.Stream]):
        self.twitch_id = twitch_id
        data = self._get_stream_data(user, stream)
        self.display_name: str = data["display_name"]
        self.name: str = data["name"]
        self.url: str = data["url"]
        self.logo_url: str = data["logo_url"]
        self.online: bool = data["online"]
        self.game: str = data["game"]
        self.title: str = data["title"]
        self.preview_url: str = data["preview_url"]

    def __repr__(self):
        return f"<Stream id={self.twitch_id} name={self.name} online={self.online} title={self.title}>"

    def _get_stream_data(self, user: twitchio.User, stream: Optional[twitchio.Stream]) -> StreamData:
        if stream:
            online = True
            game = stream.game_name
            title = stream.title
            preview_url = stream.thumbnail_url.replace("{width}", "640").replace("{height}", "360")
        else:
            online = False
            game = "Offline"
            title = "Offline"
            if user.offline_image:
                preview_url = (
                    f'{"-".join(user.offline_image.split("-")[:-1])}-640x360.{user.offline_image.split(".")[-1]}'
                )
            else:
                preview_url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{user.name}-640x360.jpg"

        return {
            "display_name": user.display_name,
            "name": user.name,
            "url": f"https://www.twitch.tv/{user.display_name}",
            "logo_url": user.profile_image,
            "online": online,
            "game": game,
            "title": title,
            "preview_url": preview_url,
        }
