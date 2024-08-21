from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, override

import discord
from discord.ext import commands

import config
from utils import const, formats

from ._base import CommunityCog

if TYPE_CHECKING:
    from twitchio.ext import eventsub

    from bot import AluBot


class TwitchCog(CommunityCog):
    @override
    async def cog_load(self) -> None:
        await self.bot.initialize_twitch()

        # Twitch EventSub
        # these are supposed to be broadcaster/user access token for streamers we sub to
        # since we are subbing to event of myself only then my own access token is fine
        broadcaster, token = const.Twitch.MY_USER_ID, config.TWITCH_ACCESS_TOKEN
        await self.bot.twitch.eventsub.subscribe_channel_stream_start(broadcaster, token)
        self.message_cache: dict[int, discord.Message] = {}
        await self.bot.twitch.eventsub.subscribe_channel_stream_end(broadcaster, token)
        # testing with channel points since it's easy yo do :D
        await self.bot.twitch.eventsub.subscribe_channel_points_redeemed(broadcaster, token)

    @commands.Cog.listener("on_twitchio_stream_start")
    async def twitch_tv_live_notifications(self, event: eventsub.StreamOnlineData) -> None:
        streamer = await self.bot.twitch.fetch_streamer(event.broadcaster.id)

        ### brute force check if internet died
        # the assumption here is that I won't take a break shorter than 1 hour between streams

        vods = await self.bot.twitch.fetch_videos(user_id=streamer.id, period="day")
        try:
            # this should always exist
            current_vod = vods[0]
            current_vod_link = f"/[VOD](f{current_vod.url})"
        except ValueError:
            current_vod = None
            current_vod_link = ""

        # to verify if the stream is truly new and avoid send duplicate notifications
        # we need to recognize the following cases:
        # * I restart the stream like a clown
        # * Internet goes down
        # * Twitch betrays me with a lag
        # * Some other F
        # we need to compare the current vod with the latest vod, because when I go offline Twitch stops the vod.

        try:
            previous_vod = vods[1]
        except ValueError:
            previous_vod = None

        if previous_vod is not None and current_vod is not None:
            previous_vod_duration = formats.hms_to_seconds(previous_vod.duration)
            estimated_prev_vod_end = previous_vod.created_at + datetime.timedelta(seconds=previous_vod_duration)

            if (current_vod.created_at - estimated_prev_vod_end).seconds < 3600:
                # we assume one of "* things" from above happened
                return

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
        self.message_cache[event.broadcaster.id] = message

    @commands.Cog.listener("on_twitchio_stream_end")
    async def twitch_tv_offline_edit_notification(self, event: eventsub.StreamOfflineData) -> None:
        try:
            message = self.message_cache[event.broadcaster.id]
        except KeyError:
            return
        embed = message.embeds[0]
        embed.set_image(
            url="https://static-cdn.jtvnw.net/jtv_user_pictures/ed948895-c574-4325-9c0c-d7639a45df64-channel_offline_image-1920x1080.png"
        )
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

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
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
    await bot.add_cog(TwitchCog(bot))
