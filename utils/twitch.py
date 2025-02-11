from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict, override

import discord
import twitchio
from twitchio import eventsub

from config import config

from . import const, fmt

if TYPE_CHECKING:
    from bot import AluBot

    class LoadTokensQueryRow(TypedDict):
        user_id: str
        token: str
        refresh: str


__all__ = ("AluTwitchClient",)

log = logging.getLogger(__name__)


class AluTwitchClient(twitchio.Client):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(
            client_id=config["TWITCH"]["CLIENT_ID"],
            client_secret=config["TWITCH"]["CLIENT_SECRET"],
            bot_id=const.TwitchID.Bot,
        )
        self._bot: AluBot = bot

    def print_bot_oauth(self) -> None:
        scopes = "%20".join(
            [
                "user:read:chat",
                "user:write:chat",
                "user:bot",
            ],
        )
        link = f"http://localhost:4343/oauth?scopes={scopes}&force_verify=true"
        print(f"🤖🤖🤖 BOT OATH LINK: 🤖🤖🤖\n{link}")  # noqa: T201

    def print_broadcaster_oauth(self) -> None:
        scopes = "%20".join(
            [
                "channel:bot",
                "channel:read:redemptions",
            ],
        )
        link = f"http://localhost:4343/oauth?scopes={scopes}&force_verify=true"
        print(f"🎬🎬🎬 BROADCASTER OATH LINK: 🎬🎬🎬\n{link}")  # noqa: T201

    @override
    async def setup_hook(self) -> None:
        # Twitchio tokens magic
        # Uncomment the following three lines and run the bot when creating tokens (otherwise they should be commented)
        # This will make the bot update the database with new tokens.
        # self.print_bot_oauth()
        # self.print_broadcaster_oauth()
        # return
        # await self.add_component(AluComponent(self))

        broadcaster = const.TwitchID.Me
        # ✅ Channel Points Redeem                 channel:read:redemptions or channel:manage:redemptions
        sub = eventsub.ChannelPointsRedeemAddSubscription(broadcaster_user_id=broadcaster)
        await self.subscribe_websocket(payload=sub, token_for=broadcaster, as_bot=False)
        # Stream went offline                   No authorization required
        sub = eventsub.StreamOfflineSubscription(broadcaster_user_id=broadcaster)
        await self.subscribe_websocket(payload=sub, token_for=broadcaster, as_bot=False)
        # Stream went live                      No authorization required
        sub = eventsub.StreamOnlineSubscription(broadcaster_user_id=broadcaster)
        await self.subscribe_websocket(payload=sub, token_for=broadcaster, as_bot=False)

    @override
    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)
        query = """
            INSERT INTO alubot_ttv_tokens (user_id, token, refresh)
            VALUES ($1, $2, $3)
            ON CONFLICT(user_id)
            DO UPDATE SET
                token = excluded.token,
                refresh = excluded.refresh;
        """
        await self._bot.pool.execute(query, resp.user_id, token, refresh)
        log.debug("Added token to the database for user: %s", resp.user_id)
        return resp

    @override
    async def load_tokens(self, path: str | None = None) -> None:
        # We don't need to call this manually, it is called in .login() from .start() internally...

        rows: list[LoadTokensQueryRow] = await self._bot.pool.fetch("""SELECT * from alubot_ttv_tokens""")
        for row in rows:
            await self.add_token(row["token"], row["refresh"])

    # @override
    async def event_ready(self) -> None:
        log.info("%s is ready as bot_id = %s", self.__class__.__name__, self.bot_id)

    # EVENT SUB

    async def event_custom_redemption_add(self, event: twitchio.ChannelPointsRedemptionAdd) -> None:
        self._bot.dispatch("twitchio_custom_redemption_add", event)

        if event.user.id == const.TwitchID.Me and event.reward.cost < 4:
            # < 4 is a weird way to exclude my "Text-To-Speech" redemption.
            # channel = self.get_channel(payload.broadcaster)
            await event.broadcaster.send_message(
                sender=const.TwitchID.Bot,
                message="Thanks, I think bot is working PepoG",
            )

    async def event_stream_offline(self, offline: twitchio.StreamOffline) -> None:
        self._bot.dispatch("twitchio_stream_offline", offline)

    async def event_stream_online(self, online: twitchio.StreamOnline) -> None:
        self._bot.dispatch("twitchio_stream_online", online)

    # OVERRIDE

    @override
    async def event_error(self, payload: twitchio.EventErrorPayload) -> None:
        embed = (
            discord.Embed(
                colour=const.Colour.twitch,
                title="TwitchIO Event Error",
            )
            .add_field(name="Exception", value=f"`{payload.error.__class__.__name__}`")
            .set_footer(
                text=f"{self.__class__.__name__}.event_error: `{payload.listener.__qualname__}`",
                icon_url=const.Logo.Twitch,
            )
        )
        await self._bot.exc_manager.register_error(payload.error, embed=embed)

    @property
    def irene(self) -> twitchio.PartialUser:
        """Get Irene's channel from the cache."""
        return self.create_partialuser(const.TwitchID.Me)

    async def fetch_streamer(self, twitch_id: str) -> Streamer:
        user = await self.create_partialuser(twitch_id).user()
        stream = next(iter(await self.fetch_streams(user_ids=[twitch_id])), None)  # None if offline
        return Streamer(self, user, stream)


# class AluComponent(commands.Component):
#     # need eventsub.ChatMessageSubscription
#     # @twitchio_commands.command()
#     # async def hi(self, ctx: twitchio_commands.Context) -> None:
#     #     """Simple command that says hello!"""
#     #     await ctx.reply("hello")

#     def __init__(self, bot: Bot) -> None:
#         self.bot = bot


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

        self.id: str = user.id
        self.display_name: str = user.display_name
        self.avatar_url: str = user.profile_image.url
        self.url: str = f"https://www.twitch.tv/{user.name}"

        if stream:
            self.live = True
            self.game = stream.game_name or "No category"
            self.title = stream.title
            # example: https://static-cdn.jtvnw.net/previews-ttv/live_user_gosu-{width}x{height}.jpg
            self.preview_url = stream.thumbnail.url
        else:
            self.live = False
            self.game = "Offline"
            self.title = "Offline"
            offline_image = user.offline_image
            if offline_image:
                # example for quinn:
                # https://static-cdn.jtvnw.net/jtv_user_pictures/fdc9e3a8-b005-4719-9ca2-1a2e0e77ff5b-channel_offline_image-640x360.png
                self.preview_url = offline_image.url
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

        duration = fmt.hms_to_seconds(video.duration)
        new_hms = fmt.divmod_timedelta(duration - seconds_ago)
        url = f"{video.url}?t={new_hms}"
        return f"/[VOD]({url})" if markdown else url

    async def game_art_url(self) -> str | None:
        """Game Art Url."""
        if self.live:
            game = next(iter(await self._twitch.fetch_games(names=[self.game])), None)
            if game:
                return game.box_art.url
        return None
