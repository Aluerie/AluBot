from __future__ import annotations

import json
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import AluContext, const

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot


class AdminTools(DevBaseCog):
    async def send_guild_embed(self, guild: discord.Guild, join: bool) -> None:
        if join:
            word, colour = "joined", const.MaterialPalette.green(shade=500)
        else:
            word, colour = "left", const.MaterialPalette.red(shade=500)

        e = discord.Embed(title=word, description=guild.description, colour=colour)
        e.add_field(name="Guild ID", value=f"`{guild.id}`")
        e.add_field(name="Shard ID", value=guild.shard_id or "N/A")

        if guild.owner:
            e.set_author(name=f"The bot {word} {guild.owner!s}'s guild", icon_url=guild.owner.display_avatar.url)
            e.add_field(name="Owner ID", value=f"`{guild.owner.id}`")

        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        bots = sum(m.bot for m in guild.members)
        total = guild.member_count or 1
        e.add_field(name="Members", value=total)
        e.add_field(name="Bots", value=f"{bots} ({bots / total:.2%})")
        if guild.me:
            e.timestamp = guild.me.joined_at
        await self.bot.hideout.global_logs.send(embed=e)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.send_guild_embed(guild, join=True)
        query = "INSERT INTO guilds (id, name) VALUES ($1, $2)"
        await self.bot.pool.execute(query, guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.send_guild_embed(guild, join=False)
        query = "DELETE FROM guilds WHERE id=$1"
        await self.bot.pool.execute(query, guild.id)

    @commands.group(name="guild", hidden=True)
    async def guild_group(self, ctx: AluContext) -> None:
        """Developer commands to control the guilds bot is in."""
        await ctx.send_help(ctx.command)

    @guild_group.command(hidden=True)
    async def leave(self, ctx: AluContext, guild: discord.Guild) -> None:
        """'Make bot leave guild with named guild_id;"""
        if guild:
            await guild.leave()
            e = discord.Embed(colour=const.Colour.blueviolet)
            e.description = f"Just left guild {guild.name} with id `{guild.id}`\n"
            await ctx.reply(embed=e)
        else:
            msg = f"The bot is not in the guild with id `{guild}`"
            raise commands.BadArgument(msg)

    @guild_group.command(hidden=True)
    async def list(self, ctx: AluContext) -> None:
        """Show list of guilds the bot is in."""
        e = discord.Embed(colour=const.Colour.blueviolet)
        e.description = (
            f"The bot is in these guilds\n"
            f"{chr(10).join([f'• {item.name} `{item.id}`' for item in self.bot.guilds])}"
        )
        await ctx.reply(embed=e)

    @guild_group.command(hidden=True)
    async def api(self, ctx: AluContext) -> None:
        """Lazy way to update GitHub ReadMe badges until I figure out more continuous one"""
        json_dict = {
            "servers": len(self.bot.guilds),
            "users": len(self.bot.users),  # [x for x in self.bot.users if not x.bot]
            "updated": discord.utils.utcnow().strftime("%d/%b/%y"),
        }
        json_object = json.dumps(json_dict, indent=4)
        await ctx.reply(content=f"```json\n{json_object}```")

    # @commands.is_owner()
    # @commands.command(hidden=True)
    # async def export_database(self, ctx: Context, db_name: str):
    #     """Export database table with `db_name` to a `.csv` file."""
    #     query = f"COPY (SELECT * FROM {db_name}) TO '/.logs/{db_name}.csv' WITH CSV DELIMITER ',' HEADER;"
    #     await ctx.pool.execute(query)
    #     await ctx.reply('Done')


async def setup(bot: AluBot) -> None:
    await bot.add_cog(AdminTools(bot))
