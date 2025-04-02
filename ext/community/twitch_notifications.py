from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, override

import discord
from discord.ext import commands

from bot import AluCog, aluloop
from utils import const

if TYPE_CHECKING:
    import twitchio

    from bot import AluBot

__all__ = ("TwitchNotifications",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class TwitchNotifications(AluCog):
    """Cog responsible for Twitch Related functions for my discord community.

    Such as
    * Notifications for my own stream start/editing when it ends;
    * giving @LiveStreamer role to folks in the server who are currently streaming on twitch.tv
    """

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.last_notification_message: discord.Message | None = None
        self.restart_clean_up.start()

    @override
    async def cog_load(self) -> None:
        await self.bot.instantiate_twitch()
        await super().cog_load()

    @commands.Cog.listener("on_twitchio_custom_redemption_add")
    async def twitch_tv_redeem_notifications(self, event: twitchio.ChannelPointsRedemptionAdd) -> None:
        """Send a notification for channel points redeems at @Irene_Adler__ into my person #logger channel.

        This is used for testing twitchio eventsub.
        """
        embed = discord.Embed(
            color=0x9146FF,
            description=f"`{event.user.name}` redeemed `{event.reward.title}` for {event.reward.cost} channel points",
        )
        await self.hideout.alubot_logs.send(embed=embed)

    @commands.Cog.listener("on_twitchio_stream_online")
    async def twitch_tv_live_notifications(self, payload: twitchio.StreamOnline) -> None:
        """Receive notifications for my stream via eventsub."""
        # I only have notifications for myself
        irene = payload.broadcaster
        irene_user = await irene.user()
        channel_info = await irene.fetch_channel_info()
        game = await channel_info.fetch_game()

        stream_url = f"https://twitch.tv/{payload.broadcaster.name}"
        current_vod = next(iter(await self.bot.twitch.fetch_videos(user_id=irene.id, period="day")), None)
        current_vod_link = f"/[VOD]({current_vod.url})" if current_vod else ""

        # send notification
        content = (
            f"{self.community.stream_lover_role.mention} and chat, "
            f"**`@{payload.broadcaster.display_name}`** just went live!"
        )
        embed = (
            discord.Embed(
                color=0x9146FF,
                title=f"{channel_info.title}",
                url=stream_url,
                description=(f"Playing {channel_info.game_name}\n/[Watch Stream]({stream_url}){current_vod_link}"),
            )
            .set_author(
                name=f"{irene.display_name} just went live on Twitch!",
                icon_url=irene_user.profile_image,
                url=stream_url,
            )
            .set_thumbnail(url=game.box_art if game else irene_user.profile_image)
            .set_image(
                url=(
                    f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{irene.display_name}-1280x720.jpg"
                    "?format=webp&width=720&height=405"
                ),
            )
        )
        self.last_notification_message = await self.community.stream_notifs.send(content=content, embed=embed)

    @commands.Cog.listener(name="on_presence_update")
    async def community_twitch_tv_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detects if community members are streaming and actions on it.

        Does the following:
        * Grant people who are streaming on twitch.tv role @LiveStreamer.
        * Gives backup for Aluerie's stream notifications (in case eventsub dies because I'm bad)
        """
        if after.guild.id != const.Guild.community:
            # not community
            return

        if before.bot or before.activities == after.activities:
            return

        before_set = {activity.type for activity in before.activities}
        after_set = {activity.type for activity in after.activities}
        if after_set == before_set:
            # sets are the same, meaning something small changed, i.e. activity property = skip
            return

        log.debug(
            "%s's presence has been updated from %s to %s",
            after.display_name,
            [item.name for item in before_set],
            [item.name for item in after_set],
        )

        streaming_type = discord.ActivityType.streaming

        if streaming_type in after_set and streaming_type not in before_set:
            live_streaming_role = self.community.live_stream_role
            if live_streaming_role not in after.roles:
                # somebody started streaming
                log.debug("Adding %s role to %s", live_streaming_role.name, after.display_name)
                await after.add_roles(live_streaming_role)

        elif streaming_type in before_set and streaming_type not in after_set:
            live_streaming_role = self.community.live_stream_role
            if live_streaming_role in after.roles:
                # somebody ended streaming
                log.debug("Removing %s role from %s", live_streaming_role.name, after.display_name)
                await before.remove_roles(live_streaming_role)
        else:
            log.debug("No Changes")
            # TODO: we need to add the voice chat thing where it checks/sets up things on restart bot
            # like get all folks with streaming status and clear the role

    @commands.Cog.listener("on_twitchio_stream_offline")
    async def twitch_tv_offline_edit_notification(self, _: twitchio.StreamOffline) -> None:
        """Starts the task to edit the notification message."""
        await asyncio.sleep(11 * 60)
        message = self.last_notification_message
        if message is None:
            return
        embed = message.embeds[0]
        embed.set_image(url=const.Twitch.MY_OFFLINE_SCREEN)
        await message.edit(embed=embed)

    @aluloop(count=1)
    async def restart_clean_up(self) -> None:
        """Do a restart clean up duty.

        * Removes @LiveStreamer role from people who are no longer streaming.
        * Adds it to people who are streaming.
        Sometimes the bot can die for a long time due to Irene^tm reasons so it's kinda necessary.
        """
        # 1. check @LiveStreamer role and remove non-streaming folks
        live_streamer_role = self.community.live_stream_role

        for member in live_streamer_role.members:
            for activity in member.activities:
                if activity.type == discord.ActivityType.streaming:
                    # user is streaming
                    break
            else:
                # user is not streaming
                await member.remove_roles(live_streamer_role)

        # 2. check who is streaming in the server right now and give them the role
        streaming_people = [
            member
            for member in self.community.guild.members
            if discord.ActivityType.streaming in {activity.type for activity in member.activities} and not member.bot
        ]
        for member in streaming_people:
            if live_streamer_role not in member.roles:
                await member.add_roles(live_streamer_role)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(TwitchNotifications(bot))
