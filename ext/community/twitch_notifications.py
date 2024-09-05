from __future__ import annotations

import asyncio
import datetime
from typing import TYPE_CHECKING, override

import discord
from discord.ext import commands

import config
from bot import AluBot, aluloop
from utils import const

from ._base import CommunityCog

if TYPE_CHECKING:
    from twitchio.ext import eventsub

    from bot import AluBot


class TwitchCog(CommunityCog):
    """Cog responsible for Twitch Related functions for my discord community.

    Such as
    * Notifications for my own stream start/editing when it ends;
    * giving @LiveStreamer role to folks in the server who are currently streaming on twitch.tv
    """

    @override
    async def cog_load(self) -> None:
        await self.bot.initialize_twitch()

        # Twitch EventSub
        # these are supposed to be broadcaster/user access token for streamers we sub to
        # since we are subbing to event of myself only then my own access token is fine
        broadcaster, token = const.Twitch.MY_USER_ID, config.TWITCH_ACCESS_TOKEN
        self.last_notification_message: discord.Message | None = None

        await self.bot.twitch.eventsub.subscribe_channel_stream_start(broadcaster, token)
        await self.bot.twitch.eventsub.subscribe_channel_stream_end(broadcaster, token)
        await self.bot.twitch.eventsub.subscribe_channel_points_redeemed(broadcaster, token)

    @commands.Cog.listener("on_twitchio_stream_start")
    async def twitch_tv_live_notifications(self, event: eventsub.StreamOnlineData) -> None:
        """Notifications for when my stream goes live.

        * Notification message has a sneak-peak image in embed that always shows the live-stream
            whenever the user enters #stream-notifications channel.
        * Also double-checks that stream is truly new, i.e. to avoid duplicate notifications in case my stream crashed.
        """
        streamer = await self.bot.twitch.fetch_streamer(event.broadcaster.id)

        # brute force check if stream died
        # due to Internet, lag, twitch being twitch or something else
        query = "SELECT twitch_last_offline FROM bot_vars"
        stream_last_offline: datetime.datetime = await self.bot.pool.fetchval(query)
        if (datetime.datetime.now(datetime.UTC) - stream_last_offline).seconds < 900:
            # the assumption here is that I won't take a break shorter than 15 minutes between streams
            self.edit_offline_screen.cancel()
            return

        current_vod = next(iter(await self.bot.twitch.fetch_videos(user_id=streamer.id, period="day")), None)
        current_vod_link = f"/[VOD]({current_vod.url})" if current_vod else ""

        ### send notification

        content = f"{self.community.stream_lover_role.mention} and chat, **`@{streamer.display_name}`** just went live!"
        embed = (
            discord.Embed(
                colour=0x9146FF,
                title=f"{streamer.title}",
                url=streamer.url,
                description=(f"Playing {streamer.game}\n/[Watch Stream]({streamer.url}){current_vod_link}"),
            )
            .set_author(
                name=f"{streamer.display_name} just went live on Twitch!",
                icon_url=streamer.avatar_url,
                url=streamer.url,
            )
            .set_image(
                url=(
                    f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{streamer.display_name}-1280x720.jpg"
                    "?format=webp&width=720&height=405"
                )
            )
        )

        if game_art_url := await streamer.game_art_url():
            embed.set_thumbnail(url=game_art_url)
        else:
            embed.set_thumbnail(url=streamer.avatar_url)

        message = await self.community.stream_notifs.send(content=content, embed=embed)
        self.last_notification_message = message

    @commands.Cog.listener("on_twitchio_stream_end")
    async def twitch_tv_offline_edit_notification(self, _: eventsub.StreamOfflineData) -> None:
        """Starts the task to edit the notification message."""
        await self.bot.pool.execute("UPDATE bot_vars SET twitch_last_offline = $1", datetime.datetime.now(datetime.UTC))
        self.edit_offline_screen.start()

    @aluloop(count=1)
    async def edit_offline_screen(self) -> None:
        """Task to edit the notification image to my offline screen when it's confirmed that stream truly ended."""
        await asyncio.sleep(11 * 60)
        message = self.last_notification_message
        if message is None:
            return
        embed = message.embeds[0]
        embed.set_image(url=const.Twitch.MY_OFFLINE_SCREEN)
        await message.edit(embed=embed)

    @commands.Cog.listener("on_twitchio_channel_points_redeem")
    async def twitch_tv_redeem_notifications(self, event: eventsub.CustomRewardRedemptionAddUpdateData) -> None:
        """Send a notification for channel points redeems at @Irene_Adler__ into my person #logger channel.

        This is used for testing twitchio eventsub.
        """
        embed = discord.Embed(
            colour=0x9146FF,
            description=f"`{event.user.name}` redeemed `{event.reward.title}` for {event.reward.cost} channel points",
        )
        await self.hideout.logger.send(embed=embed)

    @commands.Cog.listener(name="on_presence_update")
    async def live_streamer_role(self, before: discord.Member, after: discord.Member) -> None:
        """Grant people who are streaming on twitch role @LiveStreamer."""
        if before.bot or before.activities == after.activities or before.id == self.bot.owner_id:
            return

        if after.guild.id != const.Guild.community:
            # not community
            return

        live_streaming_role = self.community.live_stream_role

        stream_after = None
        for item in after.activities:
            if isinstance(item, discord.Streaming):
                stream_after = item

        # todo: voice chat role like thing as in check when the bot dies/goes back to live
        if live_streaming_role not in after.roles and stream_after is not None:  # friend started the stream
            await after.add_roles(live_streaming_role)
        elif live_streaming_role in after.roles and stream_after is None:  # friend ended the stream
            await after.remove_roles(live_streaming_role)
        else:
            return


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(TwitchCog(bot))
