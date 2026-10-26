"""LiveStreamers.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import logging
from typing import TYPE_CHECKING, Final, override

import discord
from discord.ext import commands

from core import Cog
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from core import Bot


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class LiveStreamers(Cog):
    """LiveStreamers."""

    LIVE_STREAMER_ROLE_ID: Final = const.RoleId(760082390059581471)

    @override
    async def cog_load(self) -> None:
        self.restart_clean_up.start()

    ####################################################################################################################
    # LIVE STREAMER
    ####################################################################################################################

    @staticmethod
    def _is_streaming(member: discord.Member) -> bool:
        """Return whether the member has a streaming activity on any platform."""
        return any(isinstance(a, discord.Streaming) for a in member.activities)

    async def _sync_streamer_role(self, member: discord.Member, role: discord.Role) -> None:
        """Add or remove the streamer role so it matches the member's streaming activity.

        Parameters
        ----------
        member
            The member to update.
        role
            The @LiveStreamer role.
        """
        is_streaming = self._is_streaming(member)
        has_role = role in member.roles

        try:
            if is_streaming and not has_role:
                await member.add_roles(role, reason="Started streaming")
            elif not is_streaming and has_role:
                await member.remove_roles(role, reason="Stopped streaming")
        except discord.HTTPException:
            log.exception("Failed to sync the streamer role for %s", member)

    @commands.Cog.listener(name="on_presence_update")
    async def community_streamer_role_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detect community members who are currently streaming and grant them @LiveStreamer role."""
        if after.guild.id != const.Guild.community or after.bot:
            return
        if self._is_streaming(before) == self._is_streaming(after):
            return
        await self._sync_streamer_role(after, self.bot.get_role(after.guild.id, self.LIVE_STREAMER_ROLE_ID))

    @loop(count=1, wait_for_ready=True)
    async def restart_clean_up(self) -> None:
        """Resync @LiveStreamer role after a restart.

        The bot can be offline for a long time, so presence events are missed.
        """
        role = self.bot.get_role(const.Guild.community, self.LIVE_STREAMER_ROLE_ID)
        for member in role.guild.members:
            if not member.bot:
                await self._sync_streamer_role(member, role)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(LiveStreamers(bot))
