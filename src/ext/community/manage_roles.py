"""Manage Roles.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

import discord
from discord.ext import commands

from core import AluCog
from shared.concepts import loop

if TYPE_CHECKING:
    from core import AluBot

__all__ = ("ManageRoles",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ManageRoles(AluCog):
    """Manage community roles.

    This includes:
    * Streaming on twitch.
    """

    @override
    async def cog_load(self) -> None:
        self.restart_clean_up.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.restart_clean_up.stop()
        await super().cog_unload()

    @staticmethod
    def _is_streaming(member: discord.Member) -> bool:
        return any(a.type is discord.ActivityType.streaming for a in member.activities)

    @commands.Cog.listener(name="on_presence_update")
    async def community_twitch_tv_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detect community members streaming on twitch and grant them @LiveStreamer role."""
        if after.guild.id != self.community.id or before.bot:
            return

        was_streaming, is_streaming = self._is_streaming(before), self._is_streaming(after)
        if was_streaming == is_streaming:
            return

        role = self.community.live_stream_role
        if is_streaming and role not in after.roles:
            await after.add_roles(role)
        elif not is_streaming and role in after.roles:
            await after.remove_roles(role)

    @loop(count=1, wait_for_ready=True)
    async def restart_clean_up(self) -> None:
        """Restart clean up.

        The bot can be offline for a long time, so presence events are missed:
        * Removes @LiveStreamer role from people who are no longer streaming.
        * Adds it to people who are streaming.
        """
        role = self.community.live_stream_role

        for member in role.members:
            if not self._is_streaming(member):
                await member.remove_roles(role)

        for member in self.community.guild.members:
            if not member.bot and self._is_streaming(member) and role not in member.roles:
                await member.add_roles(role)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ManageRoles(bot))
