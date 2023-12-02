from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

import config
from utils import const, twitch

from ._base import CommunityCog

if TYPE_CHECKING:
    import twitchio
    from twitchio.ext import eventsub

    from bot import AluBot


class TwitchCog(CommunityCog):
    async def cog_load(self) -> None:
        await self.bot.initiate_twitch()

        # Twitch EventSub stuff...
        # for testing we just use channel points redemptions since it's easy to do :D
        await self.bot.twitch.eventsub.subscribe_channel_stream_start(  # subscribe_channel_points_redeemed(
            broadcaster=const.MY_TWITCH_CHANNEL_ID,
            token=config.TWITCH_ALUERIE_START_STREAM_USER_TOKEN,  # TWITCH_ALUERIE_CHANNEL_POINT_REDEMPTION_USER_TOKEN
        )

    @commands.Cog.listener("on_twitchio_stream_start")
    async def twitch_tv_live_notifications(self, event: eventsub.StreamOnlineData) -> None:
        # well, we only have notifications for my own stream so id is clear :D
        # but otherwise we would need to get the id from
        me: twitchio.User = await event.broadcaster.fetch()
        me_live = next(iter(await self.bot.twitch.fetch_streams(user_ids=[me.id])), None)

        stream = twitch.TwitchStream(me.id, me, me_live)

        mention_role = self.community.stream_lover_role
        content = f"{mention_role.mention} and chat, our Highness **@{stream.display_name}** just went live !"
        file = await self.bot.imgtools.url_to_file(stream.preview_url, filename="twtvpreview.png")
        last_vod_url = await self.bot.twitch.last_vod_link(const.MY_TWITCH_CHANNEL_ID)
        desc = f"Playing {stream.game}\n/[Watch Stream]({stream.url}){last_vod_url}"
        e = discord.Embed(colour=0x9146FF, title=f"{stream.title}", url=stream.url, description=desc)
        e.set_author(name=f"{stream.display_name} just went live on Twitch!", icon_url=stream.logo_url, url=stream.url)
        e.set_thumbnail(url=stream.logo_url)
        e.set_image(url=f"attachment://{file.filename}")
        await self.community.stream_notifs.send(content=content, embed=e, file=file)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
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


async def setup(bot: AluBot):
    await bot.add_cog(TwitchCog(bot))
