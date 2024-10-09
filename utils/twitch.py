from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import discord
import twitchio
from twitchio.ext import eventsub

import config

from . import const, formats

if TYPE_CHECKING:
    from bot import AluBot


log = logging.getLogger(__name__)


class AluTwitchClient(twitchio.Client):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(token=config.TTG_ACCESS_TOKEN)

        self._bot: AluBot = bot
        self.eventsub: eventsub.EventSubWSClient = eventsub.EventSubWSClient(self)

    # EVENT SUB

    async def event_eventsub_notification(self, event: eventsub.NotificationEvent) -> None:
        match_lookup: dict[Any, str] = {
            eventsub.StreamOnlineData: "stream_start",
            eventsub.StreamOfflineData: "stream_end",
            eventsub.CustomRewardRedemptionAddUpdateData: "channel_points_redeem",  # mostly for testing
        }
        try:
            event_name = match_lookup[type(event.data)]
        except KeyError:
            # well, we don't handle said events
            return

        self._bot.dispatch(f"twitchio_{event_name}", event.data)

    # OVERRIDE

    @override
    async def event_error(self, error: Exception, data: str | None = None) -> None:
        embed = discord.Embed(
            colour=const.Colour.twitch,
            title="Twitch Client Error",
            description=data[2048:] if data else "",
        ).set_footer(text="TwitchClient.event_error", icon_url=const.Logo.Twitch)
        await self._bot.exc_manager.register_error(error, embed)

    # UTILITIES

    async def fetch_streamer(self, twitch_id: int) -> Streamer:
        user = next(iter(await self.fetch_users(ids=[twitch_id])))
        stream = next(iter(await self.fetch_streams(user_ids=[twitch_id])), None)  # None if offline
        return Streamer(self, user, stream)

    # todo: we probably want `fetch_streamers` method so we dont waste api calls, but fml - we fetch just one streamer
    # in our models


class Streamer:
    """Concatenation between `twitchio.User` and `twitch.Stream`.

    Do not confuse "streamer" with "user" or "stream" terms. This is meant to be a concatenation.
    There is a weird problem that they both don't aren't enough separately.
    While we need to fill into the same attributes for both online/offline streamers.

    Attributes
    ----------
    id: int
        Twitch user ID
    display_name: str
        Twitch user's display name with proper capitalisation
    avatar_url: str
        Profile image url, naming "avatar" is just to be somewhat consistent with discord.py
    url: str
        Link to the streamer
    live: bool
        Boolean whether the streamer is currently live/offline on twitch
    game: str
        Game name that is being streamed. "Offline" if stream is offline.
    title: str
        Stream's title. "Offline" if stream is offline.
    preview_url: str
        Thumbnail for the stream preview. Tries to use offline image if stream is offline.

    """

    if TYPE_CHECKING:
        live: bool
        game: str
        title: str
        preview_url: str

    def __init__(self, _twitch: AluTwitchClient, user: twitchio.User, stream: twitchio.Stream | None) -> None:
        self._twitch: AluTwitchClient = _twitch

        self.id: int = user.id
        self.display_name: str = user.display_name
        self.avatar_url: str = user.profile_image
        self.url: str = f"https://www.twitch.tv/{user.name}"

        if stream:
            self.live = True
            self.game = stream.game_name
            self.title = stream.title
            # example: https://static-cdn.jtvnw.net/previews-ttv/live_user_iannihilate-640x360.jpg
            self.preview_url = stream.thumbnail_url.replace("{width}", "640").replace("{height}", "360")
        else:
            self.live = False
            self.game = "Offline"
            self.title = "Offline"
            if offline_image := user.offline_image:
                # example for quinn:
                # https://static-cdn.jtvnw.net/jtv_user_pictures/fdc9e3a8-b005-4719-9ca2-1a2e0e77ff5b-channel_offline_image-640x360.png
                self.preview_url = f'{"-".join(offline_image.split("-")[:-1])}-640x360.{offline_image.split(".")[-1]}'
            else:
                # same as "if stream" but manually constructed, usually gives gray camera placeholder
                # example: https://static-cdn.jtvnw.net/previews-ttv/live_user_gorgc-640x360.jpg
                self.preview_url = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{user.name}-640x360.jpg"

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.display_name} id={self.id} title={self.title}>"

    async def vod_link(self, *, seconds_ago: int = 0, markdown: bool = True) -> str:
        """Get latest vod link, timestamped to timedelta ago."""
        video = next(iter(await self._twitch.fetch_videos(user_id=self.id, period="day")), None)
        if not video:
            return ""

        duration = formats.hms_to_seconds(video.duration)
        new_hms = formats.divmod_timedelta(duration - seconds_ago)
        url = f"{video.url}?t={new_hms}"
        return f"/[VOD]({url})" if markdown else url

    async def game_art_url(self) -> str | None:
        """Game Art Url."""
        if self.live:
            game = next(iter(await self._twitch.fetch_games(names=[self.game])), None)
            if game:
                return game.art_url(285, 380)
        return None
