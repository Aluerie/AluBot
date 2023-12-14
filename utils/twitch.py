from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

import twitchio
from discord.ext.commands import BadArgument
from twitchio.ext import eventsub

import config
from utils.formats import human_timedelta

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)


class TwitchClient(twitchio.Client):
    def __init__(self, bot: AluBot):
        super().__init__(token=config.TWITCH_ACCESS_TOKEN)

        self.discord_bot: AluBot = bot
        self.eventsub: eventsub.EventSubWSClient = eventsub.EventSubWSClient(self)

    async def event_eventsub_notification(self, event: eventsub.NotificationEvent) -> None:
        if isinstance(event.data, eventsub.StreamOnlineData):
            self.discord_bot.dispatch("twitchio_stream_start", event.data)

        # testing with channel points
        elif isinstance(event.data, eventsub.CustomRewardRedemptionAddUpdateData):
            self.discord_bot.dispatch("twitchio_channel_points_redeem", event.data)

    async def twitch_id_by_name(self, user_name: str) -> int:
        """Get twitch_id by user_login"""
        user: twitchio.User | None = next(iter(await self.fetch_users(names=[user_name])), None)
        if not user:
            raise BadArgument(f"Error checking stream `{user_name}`.\n User either does not exist or is banned.")

        return user.id

    async def name_by_twitch_id(self, user_id: int) -> str:
        """Get display_name by twitch_id"""
        user: twitchio.User | None = next(iter(await self.fetch_users(ids=[user_id])), None)
        if not user:
            raise BadArgument(f"Error checking stream `{user_id}`.\n User either does not exist or is banned.")

        return user.display_name

    async def fpc_data_by_login(self, user_login: str) -> tuple[int, str, str]:
        """Gets tuple (twitch_id, display_name) by user_login from one call to twitch client"""
        user: twitchio.User | None = next(iter(await self.fetch_users(names=[user_login])), None)
        if not user:
            raise BadArgument(f"Error checking stream `{user_login}`.\n User either does not exist or is banned.")

        return user.id, user.display_name, user.profile_image

    async def last_vod_link(self, user_id: int, seconds_ago: int = 0, md: bool = True) -> str:
        """Get last vod link for user with `user_id` with timestamp as well"""
        video: twitchio.Video | None = next(iter(await self.fetch_videos(user_id=user_id, period="day")), None)
        if not video:
            return ""

        def get_time_from_hms(hms_time: str):
            """Convert time after `?t=` in vod link into amount of seconds

            03h51m08s -> 3 * 3600 + 51 * 60 + 8 = 13868
            """

            # todo: move those two into formats or something?

            def regex_time(letter: str) -> int:
                """h -> 3, m -> 51, s -> 8 for above example"""
                pattern = r"\d+(?={})".format(letter)
                units = re.search(pattern, hms_time)
                return int(units.group(0)) if units else 0

            timeunit_dict = {"h": 3600, "m": 60, "s": 1}
            return sum([v * regex_time(letter) for letter, v in timeunit_dict.items()])

        duration = get_time_from_hms(video.duration)
        vod_url = f"{video.url}?t={human_timedelta(duration - seconds_ago, strip=True, suffix=False)}"
        return f"/[TwVOD]({vod_url})" if md else vod_url

    async def get_twitch_stream(self, twitch_id: int) -> TwitchStream:
        user = next(iter(await self.fetch_users(ids=[twitch_id])))
        stream = next(iter(await self.fetch_streams(user_ids=[twitch_id])), None)  # None if offline
        return TwitchStream(twitch_id, user, stream)


class TwitchStream:
    """My own helping class that unites twitchio.User and twitch.Stream together

    and has needed attributes, i.e. since offline users don't have `.game` data
    we fill it ourselves.
    """

    __slots__ = (
        "twitch_id",
        "display_name",
        "name",
        "game",
        "url",
        "logo_url",
        "online",
        "title",
        "preview_url",
    )

    if TYPE_CHECKING:
        display_name: str
        name: str
        game: str
        url: str
        logo_url: str
        online: bool
        title: str
        preview_url: str

    def __init__(self, twitch_id: int, user: twitchio.User, stream: Optional[twitchio.Stream]):
        self.twitch_id = twitch_id
        self._update(user, stream)

    def __repr__(self):
        return f"<Stream id={self.twitch_id} name={self.name} online={self.online} title={self.title}>"

    def _update(self, user: twitchio.User, stream: Optional[twitchio.Stream]):
        self.display_name = user.display_name
        self.name = user.name
        self.url = f"https://www.twitch.tv/{self.display_name}"
        self.logo_url = user.profile_image

        if stream:
            self.online = True
            self.game = stream.game_name
            self.title = stream.title
            self.preview_url = stream.thumbnail_url.replace("{width}", "640").replace("{height}", "360")
        else:
            self.online = False
            self.game = "Offline"
            self.title = "Offline"
            if n := user.offline_image:
                self.preview_url = f'{"-".join(n.split("-")[:-1])}-640x360.{n.split(".")[-1]}'
            else:
                self.preview_url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{self.name}-640x360.jpg"
