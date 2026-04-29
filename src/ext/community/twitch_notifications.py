from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import discord
from discord.ext import commands

from bot import AluCog, aluloop
from utils import const

if TYPE_CHECKING:
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
        self.restart_clean_up.start()

    @override
    async def cog_load(self) -> None:
        await self.bot.instantiate_twitch()
        await super().cog_load()

    @commands.Cog.listener(name="on_presence_update")
    async def community_twitch_tv_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detects if community members are streaming and actions on it.

        Grant people who are streaming on twitch.tv role @LiveStreamer.
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
