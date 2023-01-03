from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal

from os import listdir

import discord
from discord.ext import commands
import json

from .utils.bot import test_list
from .utils.checks import is_owner
from .utils.context import Context
from .utils.var import Ems, Clr, Sid, Cid, Rid, MP

if TYPE_CHECKING:
    from .utils.bot import AluBot


class AdminTools(commands.Cog, name='Tools for Bot Owner'):
    """Bot owner tools"""
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @is_owner()
    @commands.group(hidden=True)
    async def trustee(self, ctx: Context):
        await ctx.scnf()

    async def trustee_add_remove(
            self,
            ctx: Context,
            user_id: int,
            mode: Literal['add', 'remov']
    ):
        query = 'SELECT trusted_ids FROM botinfo WHERE id=$1'
        trusted_ids = await self.bot.pool.fetchval(query, Sid.alu)

        if mode == 'add':
            trusted_ids.append(user_id)
        elif mode == 'remov':
            trusted_ids.remove(user_id)

        query = 'UPDATE botinfo SET trusted_ids=$1 WHERE id=$2'
        await self.bot.pool.execute(query, trusted_ids, Sid.alu)
        e = discord.Embed(colour=Clr.prpl)
        e.description = f'We {mode}ed user with id {user_id} to the list of trusted users'
        await ctx.reply(embed=e)

    @is_owner()
    @trustee.command(hidden=True)
    async def add(self, ctx: Context, user_id: int):
        """
        Grant trustee privilege to a user with `user_id`.
        Trustees can use commands that interact with the bot database.
        """
        await self.trustee_add_remove(ctx, user_id=user_id, mode='add')

    @is_owner()
    @trustee.command(hidden=True)
    async def remove(self, ctx: Context, user_id: int):
        """Remove trustee privilege from a user with `user_id`."""
        await self.trustee_add_remove(ctx, user_id=user_id, mode='remov')

    @is_owner()
    @commands.command(hidden=True)
    async def sync(
            self,
            ctx: Context,
            guilds: commands.Greedy[discord.Object],
            spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """ Sync command. Usage examples:

        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `!sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.reply(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        fmt = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                fmt += 1
        await ctx.reply(f"Synced the tree to {fmt}/{len(guilds)} guilds.")

    @is_owner()
    @commands.command(name='extensions', hidden=True)
    async def extensions(self, ctx: Context):
        """Shows available extensions to load/reload/unload."""
        cogs = [
            f'\N{BLACK CIRCLE} {x[:-3]}'
            for x in listdir('./cogs') if x.endswith('.py')
        ] + ['\N{BLACK CIRCLE} jishaku']
        e = discord.Embed(title='Available Extensions', description='\n'.join(cogs), colour=Clr.prpl)
        await ctx.reply(embed=e)

    async def load_unload_reload_job(
            self,
            ctx: Context,
            module: str,
            *,
            mode: Literal['load', 'unload', 'reload']
    ):
        try:
            filename = f'cogs.{module.lower()}'  # so we do `$unload beta` instead of `$unload beta.py`
            match mode:
                case 'load':
                    await self.bot.load_extension(filename)
                case 'unload':
                    await self.bot.unload_extension(filename)
                case 'reload':
                    await self.reload_or_load_extension(filename)
        except commands.ExtensionError as error:
            e = discord.Embed(description=f'{error}', colour=Clr.error)
            e.set_author(name=error.__class__.__name__)
            await ctx.reply(embed=e)
        else:
            await ctx.message.add_reaction(Ems.DankApprove)

    @is_owner()
    @commands.command(name='load', hidden=True)
    async def load(self, ctx: Context, *, module: str):
        """Loads a module."""
        await self.load_unload_reload_job(ctx, module, mode='load')

    @is_owner()
    @commands.command(name='unload', hidden=True)
    async def unload(self, ctx: Context, *, module: str):
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, module, mode='unload')

    @is_owner()
    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def reload(self, ctx: Context, *, module: str):
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, module, mode='reload')

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @is_owner()
    @reload.command(name='all', hidden=True)
    async def reload_all(self, ctx: Context):
        """Reloads all modules"""
        cogs_to_reload = []
        if self.bot.test and len(test_list):
            cogs_to_reload.append('jishaku')
            for item in test_list:
                cogs_to_reload.append(f'cogs.{item}')
        else:
            cogs_to_reload.append('jishaku')
            for filename in listdir('./cogs'):
                if filename.endswith('.py'):
                    cogs_to_reload.append(f'cogs.{filename[:-3]}')

        add_reaction = True
        for cog in cogs_to_reload:
            try:
                await self.reload_or_load_extension(cog)
            except commands.ExtensionError as error:
                await ctx.reply(f'{error.__class__.__name__}: {error}')
                add_reaction = False
        if add_reaction:
            await ctx.message.add_reaction(Ems.DankApprove)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != Sid.blush:
            return
        if member.bot:
            bots_role = member.guild.get_role(Rid.waste_bots_role)
            await member.add_roles(bots_role)

    @staticmethod
    def guild_embed(guild: discord.Guild, join: bool) -> discord.Embed:
        if join:
            word, colour = 'joined', MP.green(shade=500)
        else:
            word, colour = 'was removed from', MP.red(shade=500)
        e = discord.Embed(title=guild.name, description=guild.description, colour=colour)
        e.set_author(name=f"The bot {word} {str(guild.owner)}'s guild", icon_url=guild.owner.avatar.url)
        e.set_thumbnail(url=guild.icon.url if guild.icon else None)
        e.add_field(name='Members count', value=guild.member_count)
        e.add_field(name='Guild ID', value=f'`{guild.id}`')
        return e

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.get_channel(Cid.global_logs).send(embed=self.guild_embed(guild, join=True))
        query = 'INSERT INTO guilds (id, name) VALUES ($1, $2)'
        await self.bot.pool.execute(query, guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.get_channel(Cid.global_logs).send(embed=self.guild_embed(guild, join=False))
        query = 'DELETE FROM guilds WHERE id=$1'
        await self.bot.pool.execute(query, guild.id)

    @is_owner()
    @commands.group(name='guild', hidden=True)
    async def guild_group(self, ctx: Context):
        """Group for guild commands. Use it together with subcommands"""
        await ctx.scnf()

    @is_owner()
    @guild_group.command(hidden=True)
    async def leave(self, ctx: Context, guild: discord.Guild):
        """'Make bot leave guild with named guild_id;"""
        if guild is not None:
            await guild.leave()
            e = discord.Embed(colour=Clr.prpl)
            e.description = f'Just left guild {guild.name} with id `{guild.id}`\n'
            await ctx.reply(embed=e)
        else:
            raise commands.BadArgument(f'The bot is not in the guild with id `{guild}`')

    @is_owner()
    @guild_group.command(hidden=True)
    async def list(self, ctx: Context):
        """Show list of guilds the bot is in."""
        e = discord.Embed(colour=Clr.prpl)
        e.description = (
            f"The bot is in these guilds\n"
            f"{chr(10).join([f'• {item.name} `{item.id}`' for item in self.bot.guilds])}"
        )
        await ctx.reply(embed=e)

    @is_owner()
    @guild_group.command(hidden=True)
    async def api(self, ctx: Context):
        """Lazy way to update GitHub ReadMe badges until I figure out more continuous one"""
        json_dict = {
            "servers": len(self.bot.guilds),
            "users": len(self.bot.users),  # [x for x in self.bot.users if not x.bot]
            "updated": discord.utils.utcnow().strftime('%d/%b/%y')
        }
        json_object = json.dumps(json_dict, indent=4)
        await ctx.reply(content=f'```json\n{json_object}```')


async def setup(bot: AluBot):
    await bot.add_cog(AdminTools(bot))
