"""Timezone Settings.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from core import Cog, TransformTimeZone
from shared import clock

if TYPE_CHECKING:
    from core import Bot, Interaction

__all__ = ("TimezoneSettings",)

TIME_FORMAT = "%Y-%m-%d %I:%M %p"


class TimezoneSettings(Cog):
    """Manage your timezone settings.

    Your timezone is used by the bot to understand the times you type in (reminders)
    and to show your dates correctly (birthdays).
    """

    timezone_group = app_commands.Group(
        name="timezone",
        description="Manage your timezone settings or retrieve some timezone info.",
    )

    @timezone_group.command(name="set")
    async def timezone_set(self, interaction: Interaction, timezone: TransformTimeZone) -> None:
        """Set your timezone.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands
        such as birthday set.

        Parameters
        ----------
        timezone
            The timezone to change to. Type and pick from the autocomplete or try IANA alias or country/city names.
        """
        await self.bot.tz_manager.set_timezone(interaction.user.id, timezone)
        content = f"Your timezone has been set to {timezone.label} (IANA ID: {timezone.key})."
        await interaction.response.send_message(content, ephemeral=True)

    @timezone_group.command(name="info")
    async def timezone_info(self, interaction: Interaction, timezone: TransformTimeZone) -> None:
        """Retrieve info about a timezone.

        Parameters
        ----------
        timezone
            The timezone to get info about.
        """
        now = clock.utcnow()
        local_now = now.astimezone(timezone.to_tzinfo())

        embed = (
            discord
            .Embed(color=discord.Color.blurple(), title=timezone.label)
            .add_field(name="Current Time", value=local_now.strftime(TIME_FORMAT))
            .add_field(name="UTC Offset", value=self.bot.tz_manager.get_utc_offset_string(timezone.key, now))
            .add_field(name="IANA Database Alias", value=timezone.key)
        )
        await interaction.response.send_message(embed=embed)

    @timezone_group.command(name="check")
    async def timezone_check(self, interaction: Interaction, user: discord.User | None = None) -> None:
        """Show the timezone of a user.

        Parameters
        ----------
        user
            The user to get the timezone of. Defaults to yourself if not provided.
        """
        person = user or interaction.user
        is_self = person.id == interaction.user.id

        key = await self.bot.tz_manager.get_timezone(person.id)
        if key is None:
            who = "You have" if is_self else f"{person} has"
            await interaction.response.send_message(f"{who} not set a timezone.", ephemeral=is_self)
            return

        tzinfo = await self.bot.tz_manager.get_tzinfo(person.id)
        time = clock.utcnow().astimezone(tzinfo).strftime(TIME_FORMAT)
        if is_self:
            # nobody needs to see the exact timezone of somebody else's check, so it stays private
            content = f"Your timezone is `{key}`. Your current time is {time}."
        else:
            content = f"The current time for {person} is {time}."
        await interaction.response.send_message(content, ephemeral=is_self)

    @timezone_group.command(name="clear")
    async def timezone_clear(self, interaction: Interaction) -> None:
        """Clear your timezone."""
        await self.bot.tz_manager.clear_timezone(interaction.user.id)
        await interaction.response.send_message("Your timezone has been cleared.", ephemeral=True)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(TimezoneSettings(bot))
