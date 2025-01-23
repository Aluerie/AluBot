from __future__ import annotations

import asyncio
import datetime
import zoneinfo
from typing import TYPE_CHECKING, override

import discord
from discord import app_commands

from utils.timezones import TimeZone, TimeZoneTransformer  # noqa: TC001

if TYPE_CHECKING:
    from bot import AluBot

from ._base import UserSettingsBaseCog


class TimezoneSetting(UserSettingsBaseCog):
    """Manage your timezone settings."""

    @override
    async def cog_load(self) -> None:
        self.bot.initialize_tz_manager()

    timezone_group = app_commands.Group(
        name="timezone",
        description="Manage your timezone settings or retrieve some timezone info.",
    )

    @timezone_group.command(name="set")
    async def timezone_set(
        self,
        interaction: discord.Interaction[AluBot],
        timezone: app_commands.Transform[TimeZone, TimeZoneTransformer],
    ) -> None:
        """Sets your timezone.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands
        such as birthday set.

        Parameters
        ----------
        timezone
            The timezone to change to.
        """
        await self.bot.tz_manager.set_timezone(interaction.user.id, timezone)
        content = f"Your timezone has been set to {timezone.label} (IANA ID: {timezone.key})."
        await interaction.response.send_message(content, ephemeral=True)

    @timezone_group.command(name="info")
    async def timezone_info(
        self,
        interaction: discord.Interaction[AluBot],
        timezone: app_commands.Transform[TimeZone, TimeZoneTransformer],
    ) -> None:
        """Retrieves info about a timezone.

        Parameters
        ----------
        timezone
            The timezone to get info about.
        """
        now = datetime.datetime.now(datetime.UTC)
        dt = now.astimezone(tz=zoneinfo.ZoneInfo(key=timezone.key))

        embed = (
            discord.Embed(colour=discord.Colour.blurple(), title=timezone.label)
            .add_field(name="Current Time", value=dt.strftime("%Y-%m-%d %I:%M %p"))
            .add_field(name="UTC Offset", value=self.bot.tz_manager.get_utc_offset_string(timezone.key, now))
            .add_field(name="IANA Database Alias", value=timezone.key)
        )
        await interaction.response.send_message(embed=embed)

    @timezone_group.command(name="get")
    async def timezone_get(self, interaction: discord.Interaction[AluBot], user: discord.User | None = None) -> None:
        """Shows the timezone of a user.

        Parameters
        ----------
        user
            The member to get the timezone of. Defaults to yourself.
        """
        person = user or interaction.user
        tz = await self.bot.tz_manager.get_timezone(person.id)
        if tz is None:
            await interaction.response.send_message(f"{user} has not set their timezone.")
            return

        time = discord.utils.utcnow().astimezone(zoneinfo.ZoneInfo(tz)).strftime("%Y-%m-%d %I:%M %p")
        if person.id == interaction.user.id:
            await interaction.response.send_message(f"Your timezone is {tz!r}. The current time is {time}.")
            msg = await interaction.original_response()
            await asyncio.sleep(5.0)
            await msg.edit(content=f"Your current time is {time}.")
        else:
            await interaction.response.send_message(f"The current time for {user} is {time}.")

    @timezone_group.command(name="clear")
    async def timezone_clear(self, interaction: discord.Interaction[AluBot]) -> None:
        """Clears your timezone."""
        query = "UPDATE user_settings SET timezone = NULL WHERE id=$1"
        await interaction.client.pool.execute(query, interaction.user.id)
        self.bot.tz_manager.get_timezone.invalidate(self, interaction.user.id)
        await interaction.response.send_message("Your timezone has been cleared.", ephemeral=True)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(TimezoneSetting(bot))
