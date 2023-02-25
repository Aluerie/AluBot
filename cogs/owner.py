from __future__ import annotations

import asyncio  # to expose to the eval $py command
import datetime  # to expose to the eval $py command
import inspect  # to expose to the eval $py command
import io
import json
import os
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from .lol.const import LiteralServerUpper
from .utils.bot import test_list
from .utils.checks import is_owner
from .utils.context import Context
from .utils.converters import Codeblock
from .utils.var import MP, Cid, Clr, Ems, Rid, Sid

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .dotafeed import DotaFeedToolsCog
    from .lolfeed import LoLFeedToolsCog


class AdminTools(commands.Cog, name="Tools for the Bot Owner"):
    """Bot owner tools"""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self._last_result: Optional[Any] = None
        self.sessions: set[int] = set()

    # if I ever forget to put @is_owner()
    # note that we still should put @is_owner() bcs of $help command quirk
    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @is_owner()
    @commands.group(hidden=True)
    async def trustee(self, ctx: Context):
        await ctx.scnf()

    async def trustee_add_remove(self, ctx: Context, user_id: int, mode: Literal["add", "remov"]):
        query = "SELECT trusted_ids FROM botinfo WHERE id=$1"
        trusted_ids = await self.bot.pool.fetchval(query, Sid.alu)

        if mode == "add":
            trusted_ids.append(user_id)
        elif mode == "remov":
            trusted_ids.remove(user_id)

        query = "UPDATE botinfo SET trusted_ids=$1 WHERE id=$2"
        await self.bot.pool.execute(query, trusted_ids, Sid.alu)
        e = discord.Embed(colour=Clr.prpl)
        e.description = f"We {mode}ed user with id {user_id} to the list of trusted users"
        await ctx.reply(embed=e)

    @is_owner()
    @trustee.command(hidden=True)
    async def add(self, ctx: Context, user_id: int):
        """Grant trustee privilege to a user with `user_id`.
        Trustees can use commands that interact with the bot database.
        """
        await self.trustee_add_remove(ctx, user_id=user_id, mode="add")

    @is_owner()
    @trustee.command(hidden=True)
    async def remove(self, ctx: Context, user_id: int):
        """Remove trustee privilege from a user with `user_id`."""
        await self.trustee_add_remove(ctx, user_id=user_id, mode="remov")

    @is_owner()
    @commands.command(name="extensions", hidden=True)
    async def extensions(self, ctx: Context):
        """Shows available extensions to load/reload/unload."""
        cogs = [f"\N{BLACK CIRCLE} {x[:-3]}" for x in os.listdir("./cogs") if x.endswith(".py")] + [
            "\N{BLACK CIRCLE} jishaku"
        ]
        e = discord.Embed(title="Available Extensions", description="\n".join(cogs), colour=Clr.prpl)
        await ctx.reply(embed=e)

    async def load_unload_reload_job(self, ctx: Context, module: str, *, mode: Literal["load", "unload", "reload"]):
        try:
            filename = f"cogs.{module.lower()}"  # so we do `$unload beta` instead of `$unload beta.py`
            match mode:
                case "load":
                    await self.bot.load_extension(filename)
                case "unload":
                    await self.bot.unload_extension(filename)
                case "reload":
                    await self.reload_or_load_extension(filename)
        except commands.ExtensionError as error:
            e = discord.Embed(description=f"{error}", colour=Clr.error)
            e.set_author(name=error.__class__.__name__)
            await ctx.reply(embed=e)
        else:
            await ctx.message.add_reaction(Ems.DankApprove)

    @is_owner()
    @commands.command(name="load", hidden=True)
    async def load(self, ctx: Context, *, module: str):
        """Loads a module."""
        await self.load_unload_reload_job(ctx, module, mode="load")

    @is_owner()
    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: Context, *, module: str):
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, module, mode="unload")

    @is_owner()
    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    async def reload(self, ctx: Context, *, module: str):
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, module, mode="reload")

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @is_owner()
    @reload.command(name="all", hidden=True)
    async def reload_all(self, ctx: Context):
        """Reloads all modules"""
        cogs_to_reload = []
        if self.bot.test and len(test_list):
            cogs_to_reload.append("jishaku")
            for item in test_list:
                cogs_to_reload.append(f"cogs.{item}")
        else:
            cogs_to_reload.append("jishaku")
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    cogs_to_reload.append(f"cogs.{filename[:-3]}")

        add_reaction = True
        for cog in cogs_to_reload:
            try:
                await self.reload_or_load_extension(cog)
            except commands.ExtensionError as error:
                await ctx.reply(f"{error.__class__.__name__}: {error}")
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

    async def send_guild_embed(self, guild: discord.Guild, join: bool):
        if join:
            word, colour = "joined", MP.green(shade=500)
        else:
            word, colour = "left", MP.red(shade=500)

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
        await self.bot.get_channel(Cid.global_logs).send(embed=e)

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
            e.description = f"Just left guild {guild.name} with id `{guild.id}`\n"
            await ctx.reply(embed=e)
        else:
            raise commands.BadArgument(f"The bot is not in the guild with id `{guild}`")

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
            "updated": discord.utils.utcnow().strftime("%d/%b/%y"),
        }
        json_object = json.dumps(json_dict, indent=4)
        await ctx.reply(content=f"```json\n{json_object}```")

    def get_var_dict_from_ctx(
        self, ctx: Context, mentions: Optional[List[Union[discord.User, discord.TextChannel, discord.Role]]]
    ) -> Dict[str, Any]:
        """Returns the dict to be used in eval/REPL."""
        env = {
            "author": ctx.author,
            "bot": self.bot,
            "channel": ctx.channel,
            "ctx": ctx,
            "find": discord.utils.find,
            "get": discord.utils.get,
            "guild": ctx.guild,
            "me": ctx.me,
            "message": ctx.message,
            "msg": ctx.message,
        }

        # Now let's add convertable mentions into the env
        # they will be possible to call as mention_0, user_3, role_20
        # note that number is just order in our initial message so if @John is "mention_4" then he is also "user_4"
        lookup = {
            discord.User: ["user", "mention"],
            # note: our Greedy makes member obj whenever possible on the "closest" guild
            discord.Member: ["user", "member", "mention"],
            discord.abc.GuildChannel: ["channel", "mention"],  # I hope it covers all mentionable cases fine
            discord.Role: ["role", "mention"],
        }
        if mentions:
            for idx, obj in enumerate(mentions):
                found_type: bool = False
                for discord_type in lookup:
                    if isinstance(obj, discord_type):
                        found_type = True
                        for item in lookup[discord_type]:
                            key = f"{item}_{idx}"
                            env[key] = obj
                if not found_type:
                    raise commands.BadArgument(  # should not in theory happen but let's watch out
                        f"We could not assign `mention_{idx}` to {obj} from Greedy mentions. " "Check eval cmd code."
                    )

        return env

    @is_owner()
    @commands.command(hidden=True, name="py", aliases=["eval", "python"])
    async def python(
        self,
        ctx: Context,
        mentions: commands.Greedy[Union[discord.Member, discord.User, discord.abc.GuildChannel, discord.Role]] = None,
        *,
        codeblock: Optional[Codeblock] = None,
    ):
        """Direct evaluation of Python code.
        It just puts your codeblock into `async def func():`, so
        remember to end the code with `return result` if you want only `result`
        """
        if codeblock is None:
            # codeblock is optional, just bcs I want Greedy to be optional with None and preserve the order.
            # so in the end we are free to have some "testing code" like below :D
            codeblock = Codeblock(code="print('Hello World!')", language="py")

        env = self.get_var_dict_from_ctx(ctx, mentions)
        env["_"] = (self._last_result,)
        env.update(globals())

        stdout = io.StringIO()

        # why does discord use only two spaces for tab indent
        to_compile = f'async def func():\n{textwrap.indent(codeblock.code, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as error:
            await ctx.try_tick_reaction(False)
            return await ctx.send(f"```py\n{traceback.format_exc()}```")

        func = env["func"]  # <class 'function'>

        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as error:
            value = stdout.getvalue()
            await ctx.try_tick_reaction(False)
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            await ctx.try_tick_reaction(True)

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    db = app_commands.Group(
        name="db",
        description="Group command about managing database",
        guild_ids=[Sid.test],
    )

    db_dota = app_commands.Group(
        name="dota",
        description="Group command about managing Dota 2 database",
        parent=db,
    )

    def get_dota_tools_cog(self) -> DotaFeedToolsCog:
        """Get dota tools cog"""
        dota_cog: Optional[DotaFeedToolsCog] = self.bot.get_cog('Dota 2')  # type:ignore
        if dota_cog is None:
            # todo: sort this out when we gonna do error handler refactor
            raise commands.ExtensionNotLoaded(name='Dota 2 Cog is not loaded')
        return dota_cog

    @db_dota.command(name="add")
    async def db_dota_add(self, ntr: discord.Interaction[AluBot], name: str, steam: str, twitch: bool):
        """Add player to the database.

        Parameters
        ----------
        ntr: discord.Interaction
        name:
            Player name. If it is a twitch tv streamer then provide their twitch handle.
        steam:
            Steamid in any of 64/32/3/2 versions, friend_id or just steam profile link.
        twitch:
            If you proved twitch handle for "name" then press `True` otherwise `False`.

        """

        dota_cog = self.get_dota_tools_cog()
        player_dict = await dota_cog.get_player_dict(name_flag=name, twitch_flag=twitch)
        account_dict = await dota_cog.get_account_dict(steam_flag=steam)
        await dota_cog.database_add(ntr, player_dict, account_dict)

    @db_dota.command(name='remove')
    async def db_dota_remove(self, ntr: discord.Interaction[AluBot], name: str, steam: Optional[str]):
        """Remove account/player from the database.

        Parameters
        ----------
        ntr :
        name :
            Twitch.tv stream name.
        steam :
            Steam_id in any of 64/32/3/2 versions, friend_id or just Steam profile link.
        """

        dota_cog = self.get_dota_tools_cog()
        if steam:
            steam_id, _ = dota_cog.get_steam_id_and_64(steam)
        else:
            steam_id = None
        await dota_cog.database_remove(ntr, name.lower(), steam_id)

    db_lol = app_commands.Group(
        name="lol",
        description="Group command about managing Dota 2 database",
        parent=db,
    )

    def get_lol_tools_cog(self) -> LoLFeedToolsCog:
        """Get lol tools cog"""
        lol_cog: Optional[LoLFeedToolsCog] = self.bot.get_cog('LoL')  # type:ignore
        if lol_cog is None:
            # todo: sort this out when we gonna do error handler refactor
            raise commands.ExtensionNotLoaded(name='Dota 2 Cog is not loaded')
        return lol_cog

    @db_lol.command(name='add')
    async def db_lol_add(self, ntr: discord.Interaction[AluBot], name: str, server: LiteralServerUpper, account: str):
        """Add player to the database.

        Parameters
        ----------
        ntr: discord.Interaction[AluBot]
        name:
            Twitch.tv player\'s handle
        server:
            Server of the account, i.e. "NA", "EUW"
        account:
            Summoner name of the account
        """

        lol_cog = self.get_lol_tools_cog()
        player_dict = await lol_cog.get_player_dict(name_flag=name, twitch_flag=True)
        account_dict = await lol_cog.get_account_dict(server=server, account=account)
        await lol_cog.database_add(ntr, player_dict, account_dict)

    @db_lol.command(name='remove')
    async def db_lol_remove(
        self, ntr: discord.Interaction[AluBot], name: str, server: Optional[LiteralServerUpper], account: Optional[str]
    ):
        """Remove account/player from the database.

        Parameters
        ----------
        ntr: discord.Interaction[AluBot]
        name:
            Twitch.tv player name
        server:
            Server region of the account
        account:
            Summoner name of the account
        """

        lol_cog = self.get_lol_tools_cog()
        if bool(server) != bool(account):
            raise commands.BadArgument('You need to provide both `server` and `account` to delete the specific account')
        elif server:
            # todo: check type str | None for account
            lol_id, _, _ = lol_cog.get_lol_id(server=server, account=account)
        else:
            lol_id = None
        await lol_cog.database_remove(ntr, name.lower(), lol_id)


async def setup(bot: AluBot):
    await bot.add_cog(AdminTools(bot))
