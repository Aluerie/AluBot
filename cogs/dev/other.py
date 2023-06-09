from __future__ import annotations

import json
from typing import TYPE_CHECKING, Awaitable, Callable, List, Literal

import discord
from discord.ext import commands

from cogs import INITIAL_EXTENSIONS, get_extensions
from utils import AluGuildContext, const
from utils.checks import is_owner

from ._base import DevBaseCog

if TYPE_CHECKING:
    pass


class AdminTools(DevBaseCog):
    @is_owner()
    @commands.group(hidden=True)
    async def trustee(self, ctx: AluGuildContext):
        # TODO: move this garbage to FPC or bot management.
        await ctx.scnf()

    async def get_trusted_ids(self) -> List[int]:
        query = "SELECT trusted_ids FROM botinfo WHERE id=$1"
        return await self.bot.pool.fetchval(query, const.Guild.community)

    async def trustee_add_remove(self, ctx: AluGuildContext, user_id: int, mode: Literal["add", "remov"]):
        trusted_ids = await self.get_trusted_ids()
        if mode == "add":
            trusted_ids.append(user_id)
        elif mode == "remov":
            trusted_ids.remove(user_id)

        query = "UPDATE botinfo SET trusted_ids=$1 WHERE id=$2"
        await self.bot.pool.execute(query, trusted_ids, const.Guild.community)
        e = discord.Embed(colour=const.Colour.prpl())
        e.description = f"We {mode}ed user with id {user_id} to the list of trusted users"
        await ctx.reply(embed=e)

    @is_owner()
    @trustee.command(hidden=True)
    async def add(self, ctx: AluGuildContext, user_id: int):
        """Grant trustee privilege to a user with `user_id`.
        Trustees can use commands that interact with the bot database.
        """
        await self.trustee_add_remove(ctx, user_id=user_id, mode="add")

    @is_owner()
    @trustee.command(hidden=True)
    async def remove(self, ctx: AluGuildContext, user_id: int):
        """Remove trustee privilege from a user with `user_id`."""
        await self.trustee_add_remove(ctx, user_id=user_id, mode="remov")

    @is_owner()
    @trustee.command(name='list', hidden=True)
    async def list_(self, ctx: AluGuildContext):
        """Get list of trusted users."""
        trusted_ids = await self.get_trusted_ids()
        msg = '\n'.join([f'\N{BLACK CIRCLE} {ctx.bot.get_user(i)} - `{i}`' for i in trusted_ids])
        e = discord.Embed(color=const.Colour.prpl(), title='List of trustees', description=msg)
        await ctx.reply(embed=e)

    @is_owner()
    @commands.command(name="extensions", hidden=True)
    async def extensions(self, ctx: AluGuildContext):
        """Shows available extensions to load/reload/unload."""
        exts = [f"\N{BLACK CIRCLE} {ext[5:] if ext.startswith('cogs.') else ext}" for ext in self.bot.extensions.keys()]
        e = discord.Embed(title="Available Extensions", description="\n".join(exts), colour=const.Colour.prpl())
        await ctx.reply(embed=e)

    async def load_unload_reload_job(
        self, ctx: AluGuildContext, module: str, *, job_func: Callable[[str], Awaitable[None]]
    ):
        try:
            # so we do `$unload beta` instead of `$unload beta.py`
            m = module.lower()
            filename = f"cogs.{m}" if m not in INITIAL_EXTENSIONS else m
            await job_func(filename)
        except commands.ExtensionError as error:
            e = discord.Embed(description=f"{error}", colour=const.Colour.error())
            e.set_author(name=error.__class__.__name__)
            await ctx.reply(embed=e)
        else:
            await ctx.message.add_reaction(const.Emote.DankApprove)

    @is_owner()
    @commands.command(name="load", hidden=True)
    async def load(self, ctx: AluGuildContext, *, module: str):
        """Loads a module."""
        await self.load_unload_reload_job(ctx, module, job_func=self.bot.load_extension)

    @is_owner()
    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: AluGuildContext, *, module: str):
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, module, job_func=self.bot.unload_extension)

    @is_owner()
    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    async def reload(self, ctx: AluGuildContext, *, module: str):
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, module, job_func=self.reload_or_load_extension)

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @is_owner()
    @reload.command(name="all", hidden=True)
    async def reload_all(self, ctx: AluGuildContext):
        """Reloads all modules"""
        cogs_to_reload = get_extensions(ctx.bot.test)

        add_reaction = True
        for cog in cogs_to_reload:
            try:
                await self.reload_or_load_extension(cog)
            except commands.ExtensionError as error:
                await ctx.reply(f"{error.__class__.__name__}: {error}")
                add_reaction = False
        if add_reaction:
            await ctx.message.add_reaction(const.Emote.DankApprove)

    async def send_guild_embed(self, guild: discord.Guild, join: bool):
        if join:
            word, colour = "joined", const.MaterialPalette.green(shade=500)
        else:
            word, colour = "left", const.MaterialPalette.red(shade=500)

        e = discord.Embed(title=word, description=guild.description, colour=colour)
        e.add_field(name="Guild ID", value=f"`{guild.id}`")
        e.add_field(name="Shard ID", value=guild.shard_id or "N/A")

        if guild.owner:
            e.set_author(name=f"The bot {word} {str(guild.owner)}'s guild", icon_url=guild.owner.display_avatar.url)
            e.add_field(name="Owner ID", value=f"`{guild.owner.id}`")

        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        bots = sum(m.bot for m in guild.members)
        total = guild.member_count or 1
        e.add_field(name="Members", value=total)
        e.add_field(name="Bots", value=f"{bots} ({bots / total:.2%})")
        e.timestamp = guild.me.joined_at
        await self.bot.hideout.global_logs.send(embed=e)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.send_guild_embed(guild, join=True)
        query = "INSERT INTO guilds (id, name) VALUES ($1, $2)"
        await self.bot.pool.execute(query, guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.send_guild_embed(guild, join=False)
        query = "DELETE FROM guilds WHERE id=$1"
        await self.bot.pool.execute(query, guild.id)

    @is_owner()
    @commands.group(name="guild", hidden=True)
    async def guild_group(self, ctx: AluGuildContext):
        """Group for guild commands. Use it together with subcommands"""
        await ctx.scnf()

    @is_owner()
    @guild_group.command(hidden=True)
    async def leave(self, ctx: AluGuildContext, guild: discord.Guild):
        """'Make bot leave guild with named guild_id;"""
        if guild is not None:
            await guild.leave()
            e = discord.Embed(colour=const.Colour.prpl())
            e.description = f"Just left guild {guild.name} with id `{guild.id}`\n"
            await ctx.reply(embed=e)
        else:
            raise commands.BadArgument(f"The bot is not in the guild with id `{guild}`")

    @is_owner()
    @guild_group.command(hidden=True)
    async def list(self, ctx: AluGuildContext):
        """Show list of guilds the bot is in."""
        e = discord.Embed(colour=const.Colour.prpl())
        e.description = (
            f"The bot is in these guilds\n"
            f"{chr(10).join([f'• {item.name} `{item.id}`' for item in self.bot.guilds])}"
        )
        await ctx.reply(embed=e)

    @is_owner()
    @guild_group.command(hidden=True)
    async def api(self, ctx: AluGuildContext):
        """Lazy way to update GitHub ReadMe badges until I figure out more continuous one"""
        json_dict = {
            "servers": len(self.bot.guilds),
            "users": len(self.bot.users),  # [x for x in self.bot.users if not x.bot]
            "updated": discord.utils.utcnow().strftime("%d/%b/%y"),
        }
        json_object = json.dumps(json_dict, indent=4)
        await ctx.reply(content=f"```json\n{json_object}```")

    # @is_owner()
    # @commands.command(hidden=True)
    # async def export_database(self, ctx: Context, db_name: str):
    #     """Export database table with `db_name` to a `.csv` file."""
    #     query = f"COPY (SELECT * FROM {db_name}) TO '/.logs/{db_name}.csv' WITH CSV DELIMITER ',' HEADER;"
    #     await ctx.pool.execute(query)
    #     await ctx.reply('Done')
