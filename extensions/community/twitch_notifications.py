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
        await self.bot.initialize_twitch()

        # Twitch EventSub
        # these are supposed to be broadcaster/user access token for streamers we sub to
        # since we are subbing to event of myself only then my own access token is fine
        broadcaster, token = const.Twitch.my_channel_id, config.TWITCH_ACCESS_TOKEN
        await self.bot.twitch.eventsub.subscribe_channel_stream_start(broadcaster, token)
        # testing with channel points since it's easy yo do :D
        await self.bot.twitch.eventsub.subscribe_channel_points_redeemed(broadcaster, token)

    @commands.Cog.listener("on_twitchio_stream_start")
    async def twitch_tv_live_notifications(self, event: eventsub.StreamOnlineData) -> None:
        streamer = await self.bot.twitch.fetch_streamer(event.broadcaster.id)

        content = (
            f"{self.community.stream_lover_role.mention} and chat, "
            + f"our Highness **@{streamer.display_name}** just went live !"
        )
        file = await self.bot.transposer.url_to_file(streamer.preview_url, filename="twtvpreview.png")
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
            .set_image(url=f"attachment://{file.filename}")
        )

        if game_art_url := await streamer.game_art_url():
            embed.set_thumbnail(url=game_art_url)
        else:
            embed.set_thumbnail(url=streamer.avatar_url)

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
