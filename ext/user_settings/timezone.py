from __future__ import annotations

import asyncio
import zoneinfo
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils.timezones import TimeZone, TimeZoneTransformer  # noqa: TCH001

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

from ._base import UserSettingsBaseCog


class TimezoneSetting(UserSettingsBaseCog):
    async def cog_load(self) -> None:
        self.bot.initialize_tz_manager()

    @commands.hybrid_group()
    async def timezone(self, ctx: AluContext) -> None:
        """Commands related to managing or retrieving timezone info."""
        await ctx.send_help(ctx.command)

    @timezone.command(name="set")
    @app_commands.describe(timezone="The timezone to change to.")
    async def timezone_set(
        self, ctx: AluContext, *, timezone: app_commands.Transform[TimeZone, TimeZoneTransformer]
    ) -> None:
        """Sets your timezone.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands
        such as birthday set.
        """
        await self.bot.tz_manager.set_timezone(ctx.author.id, timezone)
        content = f"Your timezone has been set to {timezone.label} (IANA ID: {timezone.key})."
        await ctx.send(content, ephemeral=True)

    @timezone.command(name="info")
    @app_commands.describe(timezone="The timezone to get info about.")
    async def timezone_info(
        self, ctx: AluContext, *, timezone: app_commands.Transform[TimeZone, TimeZoneTransformer]
    ) -> None:
        """Retrieves info about a timezone."""
        e = discord.Embed(title=timezone.label, colour=discord.Colour.blurple())
        now_utc = discord.utils.utcnow()
        dt = now_utc.astimezone(tz=zoneinfo.ZoneInfo(key=timezone.key))
        e.add_field(name="Current Time", value=dt.strftime("%Y-%m-%d %I:%M %p"))
        e.add_field(name="UTC Offset", value=self.bot.tz_manager.get_utc_offset_string(timezone.key, now_utc))
        e.add_field(name="IANA Database Alias", value=timezone.key)

        await ctx.send(embed=e)

    @timezone.command(name="get")
    @app_commands.describe(user="The member to get the timezone of. Defaults to yourself.")
    async def timezone_get(self, ctx: AluContext, *, user: discord.User = commands.Author) -> None:
        """Shows the timezone of a user."""
        self_query = user.id == ctx.author.id
        tz = await self.bot.tz_manager.get_timezone(user.id)
        if tz is None:
            await ctx.send(f"{user} has not set their timezone.")
            return

        time = discord.utils.utcnow().astimezone(zoneinfo.ZoneInfo(tz)).strftime("%Y-%m-%d %I:%M %p")
        if self_query:
            msg = await ctx.send(f"Your timezone is {tz!r}. The current time is {time}.")
            await asyncio.sleep(5.0)
            await msg.edit(content=f"Your current time is {time}.")
        else:
            await ctx.send(f"The current time for {user} is {time}.")

    @timezone.command(name="clear")
    async def timezone_clear(self, ctx: AluContext) -> None:
        """Clears your timezone."""
        await ctx.pool.execute("UPDATE user_settings SET timezone = NULL WHERE id=$1", ctx.author.id)
        self.bot.tz_manager.get_timezone.invalidate(self, ctx.author.id)
        await ctx.send("Your timezone has been cleared.", ephemeral=True)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(TimezoneSetting(bot))
