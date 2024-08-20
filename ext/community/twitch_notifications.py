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

        video = next(iter(await self.bot.twitch.fetch_videos(user_id=streamer.id, period="day")), None)
        if video:
            duration = formats.hms_to_seconds(video.duration)
            estimated_video_end = video.created_at + datetime.timedelta(seconds=duration)

            now = datetime.datetime.now(datetime.UTC)
            if (now - estimated_video_end).seconds < 3600:
                # my internet probably crashed or twitch died, or I manually restarted the stream.
                return

        ### send notification

        content = f"{self.community.stream_lover_role.mention} and chat, **`@{streamer.display_name}`** just went live!"
        embed = (
            discord.Embed(
                colour=0x9146FF,
                title=f"{streamer.title}",
                url=streamer.url,
                description=(f"Playing {streamer.game}\n/[Watch Stream]({streamer.url}){await streamer.vod_link()}"),
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
        embed = discord.Embed(
            colour=0x9146FF,
            description=f"`{event.user.name}` redeemed `{event.reward.title}` for {event.reward.cost} channel points",
        )
        await self.hideout.spam.send(embed=embed)

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
