from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

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

        # Twitch EventSub
        # these are supposed to be broadcaster/user access token for streamers we sub to
        # since we are subbing to event of myself only then my own access token is fine
        broadcaster, token = const.Twitch.my_channel_id, config.TWITCH_ACCESS_TOKEN
        await self.bot.twitch.eventsub.subscribe_channel_stream_start(broadcaster, token)
        # testing with channel points since it's easy yo do :D
        await self.bot.twitch.eventsub.subscribe_channel_points_redeemed(broadcaster, token)

    @commands.Cog.listener("on_twitchio_stream_start")
    async def twitch_tv_live_notifications(self, event: eventsub.StreamOnlineData) -> None:
        me: twitchio.User = await event.broadcaster.fetch()
        me_live = next(iter(await self.bot.twitch.fetch_streams(user_ids=[me.id])), None)

        stream = twitch.TwitchStream(me.id, me, me_live)

        mention_role = self.community.stream_lover_role
        content = f"{mention_role.mention} and chat, our Highness **@{stream.display_name}** just went live !"
        file = await self.bot.transposer.url_to_file(stream.preview_url, filename="twtvpreview.png")
        last_vod_url = await self.bot.twitch.last_vod_link(const.Twitch.my_channel_id)
        desc = f"Playing {stream.game}\n/[Watch Stream]({stream.url}){last_vod_url}"
        embed = discord.Embed(colour=0x9146FF, title=f"{stream.title}", url=stream.url, description=desc)
        embed.set_author(
            name=f"{stream.display_name} just went live on Twitch!", icon_url=stream.logo_url, url=stream.url
        )

        # game art thumbnail
        game = next(iter(await self.bot.twitch.fetch_games(names=[stream.game])), None)
        if game:
            embed.set_thumbnail(url=game.art_url(285, 380))

        embed.set_thumbnail(url=stream.logo_url)
        embed.set_image(url=f"attachment://{file.filename}")
        await self.community.stream_notifs.send(content=content, embed=embed, file=file)

    @commands.Cog.listener("on_twitchio_channel_points_redeem")
    async def twitch_tv_redeem_notifications(self, event: eventsub.CustomRewardRedemptionAddUpdateData) -> None:
        e = discord.Embed(colour=0x9146FF)
        e.description = f"{event.user.name} redeemed {event.reward.title} for {event.reward.cost} channel points"
        await self.hideout.spam.send(embed=e)

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